"""Opt-in checks against an installed CUGA runtime, with no hosted model calls.

Run with CUGA_RUNTIME_TESTS=1 in a CUGA environment; see docs/builder-validation.md.
The model and embeddings are deterministic test doubles. SDK, loaders, SQLite,
policy matching, Manage routes and config versioning are the real implementation.
"""

import asyncio
import inspect
import json
import os
import re
from types import SimpleNamespace

import pytest

from cuga_harness_kit.cli import SKILLS_DIR

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("CUGA_RUNTIME_TESTS") != "1", reason="opt-in installed CUGA runtime"
    ),
]


def blocks(skill, language):
    text = (SKILLS_DIR / skill / "SKILL.md").read_text()
    return re.findall(rf"^```{language}\n(.*?)^```", text, re.MULTILINE | re.DOTALL)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    # Import only after isolating paths; never use an operator's config database.
    monkeypatch.setenv("CUGA_DBS_DIR", str(tmp_path))
    monkeypatch.setenv("DYNACONF_STORAGE__LOCAL_DB_PATH", str(tmp_path / "cuga.db"))
    monkeypatch.setenv("DYNACONF_STORAGE__MODE", "local")
    monkeypatch.setenv("DYNACONF_KNOWLEDGE__ENABLED", "false")
    monkeypatch.setenv("DYNACONF_AUTH__ENABLED", "false")
    monkeypatch.delenv("CUGA_MANAGER_MODE", raising=False)
    from cuga.backend.llm.models import LLMManager
    from cuga.backend.storage import get_storage
    from cuga.config import settings
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    settings.set("storage.local_db_path", str(tmp_path / "cuga.db"))
    settings.set("storage.mode", "local")
    settings.set("knowledge.enabled", False)
    settings.set("auth.enabled", False)
    settings.set("supervisor.registry_enabled", False)
    get_storage().invalidate_relational_stores()

    class NoModelCalls(FakeListChatModel):
        def _call(self, *args, **kwargs):
            raise AssertionError("This check must not call an LLM")

    model = NoModelCalls(responses=["unused"])
    monkeypatch.setattr(LLMManager, "get_model", lambda *args, **kwargs: model)
    yield model
    get_storage().invalidate_relational_stores()


def policy_storage(tmp_path, collection="harness"):
    from cuga.backend.cuga_graph.policy.storage import PolicyStorage
    from cuga.backend.storage.policy.local import LocalPolicyStore

    storage = PolicyStorage(
        backend=LocalPolicyStore(str(tmp_path / "policies.db"), collection),
        embedding_dim=3,
    )

    # Provider boundary only: loaders and persistence still execute normally.
    async def embed(texts):
        return [1.0, 0.0, 0.0]

    storage._embedding_function = embed
    storage._embedding_initialized = True
    return storage


def test_documented_policy_files_load_all_five_types(runtime, tmp_path):
    from cuga.backend.cuga_graph.policy.folder_loader import load_policies_from_folder

    templates = blocks("author-policy", "markdown")
    assert len(templates) == 5
    text = (SKILLS_DIR / "author-policy" / "SKILL.md").read_text()
    paths = re.findall(r"^### .* — `(\.cuga/[^`]+)`", text, re.MULTILINE)
    assert len(paths) == len(templates)
    for path, content in zip(paths, templates):
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    async def check():
        storage = policy_storage(tmp_path)
        await storage.initialize_async()
        try:
            loaded = await load_policies_from_folder(str(tmp_path / ".cuga"), storage)
            assert loaded["errors"] == []
            assert loaded["count"] == 5
            policies = await storage.list_policies()
            assert {p.type.value for p in policies} == {
                "intent_guard",
                "playbook",
                "tool_guide",
                "tool_approval",
                "output_formatter",
            }
            by_id = {p.id: p for p in policies}
            assert (
                by_id["guard_delete"].response.content.strip()
                == "Deletion operations are not permitted for security reasons."
            )
            assert "exact order_id" in by_id["guide_lookup"].guide_content
            assert (
                "Confirm before continuing" in by_id["approval_delete"].approval_message
            )
            assert json.loads(by_id["formatter_summary"].format_config)["required"] == [
                "summary"
            ]
        finally:
            await storage.disconnect()

    asyncio.run(check())


def test_sdk_tools_and_keyword_guard_invoke(runtime, tmp_path):
    from cuga import CugaAgent, CugaSupervisor
    from cuga.backend.cuga_graph.policy.agent import PolicyContext
    from cuga.backend.cuga_graph.policy.configurable import PolicyConfigurable

    # Execute the published tool definition, not a duplicate implementation.
    source = blocks("build-agent", "python")[0].split("async def main():")[0]
    namespace = {}
    exec(source, namespace)  # noqa: S102 - executes a trusted, shipped example
    add_numbers = namespace["add_numbers"]

    async def check():
        storage = policy_storage(tmp_path)
        await storage.initialize_async()
        system = PolicyConfigurable(storage=storage, llm=runtime)
        agent = CugaAgent(
            tools=[add_numbers],
            model=runtime,
            policy_system=system,
            enable_knowledge=False,
            auto_load_policies=False,
            filesystem_sync=False,
        )
        supervisor = CugaSupervisor(
            agents={"math": agent}, model=runtime, policy_system=system
        )
        try:
            await agent.initialize()
            tools = await agent.tool_provider.get_all_tools()
            assert len(tools) == 1
            assert await tools[0].ainvoke({"a": 5, "b": 3}) == 8
            snippet = blocks("author-policy", "python")[0]

            # Execute the exact documented coroutine with only constructor provider injection.
            def configured_agent(**kwargs):
                return CugaAgent(model=runtime, policy_system=system, **kwargs)

            ns = {"__name__": "harness_test"}
            snippet = snippet.replace("from cuga import CugaAgent\n", "").replace(
                "asyncio.run(main())", ""
            )
            ns["CugaAgent"] = configured_agent
            exec(snippet, ns)  # noqa: S102 - executes a trusted, shipped example
            await ns["main"]()
            match = await system.match_policy(
                PolicyContext(user_input="read the records")
            )
            assert not match.matched
            assert inspect.iscoroutinefunction(CugaSupervisor.from_yaml)
        finally:
            await supervisor.aclose()
            await agent.aclose()
            await storage.disconnect()

    asyncio.run(check())


def test_documented_managed_guard_and_config_publish(runtime, tmp_path):
    from cuga.backend.cuga_graph.policy.configurable import PolicyConfigurable
    from cuga.backend.cuga_graph.policy.models import IntentGuard
    from cuga.backend.server.config_store import load_draft, reset_config_db
    from cuga.backend.server.manage_routes import router
    from cuga.backend.server.managed_mcp import tools_to_registry_yaml
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    policy = IntentGuard.model_validate(json.loads(blocks("managed-server", "json")[0]))
    assert policy.triggers[0].value == ["delete", "remove"]
    reset_config_db()
    app = FastAPI()
    app.include_router(router)

    async def make_system(collection):
        storage = policy_storage(tmp_path, collection)
        await storage.initialize_async()
        system = PolicyConfigurable(storage=storage, llm=runtime)
        await system.initialize()
        return system

    published_system = asyncio.run(make_system("published"))
    draft_system = asyncio.run(make_system("draft"))
    app.state.app_state = SimpleNamespace(
        knowledge_engine=None,
        agent=None,
        policy_system=published_system,
        policy_filesystem_sync=False,
        agent_graphs_cache={},
    )
    app.state.draft_app_state = SimpleNamespace(
        agent=None,
        policy_system=draft_system,
        policy_filesystem_sync=False,
        tools_include_version=0,
    )
    params = {"agent_id": "cuga-default"}
    config = {
        "agent": {"name": "Harness Test"},
        "knowledge": {"enabled": False},
        "llm": {"api_key": "harness-test-placeholder"},
        "tools": [],
        "policies": [policy.model_dump(mode="json")],
    }
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/manage/config/draft", params=params, json={"config": config}
            ).status_code
            == 200
        )
        assert (
            client.get("/api/manage/config", params={**params, "draft": "1"}).json()[
                "config"
            ]["agent"]["name"]
            == "Harness Test"
        )
        assert client.get("/api/manage/config", params=params).json()["config"] == {}
        # A redacted GET is not a complete publish source. A narrow PATCH
        # preserves credentials in the server's stored draft.
        redacted = client.get(
            "/api/manage/config", params={**params, "draft": "1"}
        ).json()["config"]
        assert redacted["llm"]["api_key"] == ""
        assert (
            client.patch(
                "/api/manage/config/draft/agent",
                params=params,
                json={"agent": {"name": "Patched Draft"}},
            ).status_code
            == 200
        )
        assert (
            asyncio.run(load_draft("cuga-default"))["llm"]["api_key"]
            == "harness-test-placeholder"
        )
        assert asyncio.run(published_system.storage.list_policies()) == []
        assert len(asyncio.run(draft_system.storage.list_policies())) == 1
        first = client.post(
            "/api/manage/config", params=params, json={"config": config}
        )
        assert first.status_code == 200, first.text
        assert first.json()["version"] == "1"
        assert (
            asyncio.run(load_draft("cuga-default"))["llm"]["api_key"]
            == "harness-test-placeholder"
        )
        config["agent"]["name"] = "Draft Only"
        config["policies"][0]["response"]["content"] = "Draft guard response"
        assert (
            client.post(
                "/api/manage/config/draft", params=params, json={"config": config}
            ).status_code
            == 200
        )
        saved = client.get("/api/manage/config", params=params).json()
        assert saved["version"] == "1"
        assert saved["config"]["agent"]["name"] == "Harness Test"
        assert (
            asyncio.run(published_system.storage.list_policies())[0].response.content
            == policy.response.content
        )
        assert (
            asyncio.run(draft_system.storage.list_policies())[0].response.content
            == "Draft guard response"
        )
        second = client.post(
            "/api/manage/config", params=params, json={"config": config}
        )
        assert second.status_code == 200, second.text
        assert second.json()["version"] == "2"
        assert (
            client.get("/api/manage/config", params=params).json()["config"]["agent"][
                "name"
            ]
            == "Draft Only"
        )
        assert (
            asyncio.run(published_system.storage.list_policies())[0].response.content
            == "Draft guard response"
        )
        assert (
            client.post(
                "/api/manage/config", params=params, json={"config": {"agent": {}}}
            ).status_code
            == 400
        )

    tools = [
        {
            "name": "orders",
            "type": "mcp",
            "url": "http://localhost:9000/mcp",
            "transport": "http",
        },
        {
            "name": "api",
            "type": "openapi",
            "url": "http://localhost:9000/openapi.json",
            "include": ["lookupOrder"],
        },
    ]
    registry = tools_to_registry_yaml(tools)
    assert registry["mcpServers"]["orders"]["transport"] == "http"
    assert registry["services"][0]["api"]["include"] == ["lookupOrder"]


def test_runtime_skill_template_discovery_and_load(runtime, tmp_path):
    from cuga.backend.skills.loader import discover_skills
    from cuga.backend.skills.registry import SkillRegistry

    template = blocks("build-cuga-skill", "markdown")[0]
    folder = tmp_path / ".cuga" / "skills" / "my-skill"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(template)
    entries = discover_skills(str(tmp_path / ".cuga"), root="cuga")
    assert len(entries) == 1
    assert entries[0].name == "my-skill"
    assert entries[0].requirements == ("some-pip-package",)
    assert "# My Skill" in SkillRegistry(entries).load_skill("my-skill")


def test_run_api_requires_configured_gateway_token(runtime, monkeypatch):
    from cuga.backend.server.run_routes import build_run_router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    async def unused_stream(*args, **kwargs):
        raise AssertionError("Authentication must run before agent execution")
        yield

    monkeypatch.setenv("CUGA_RUN_TOKEN", "harness-test-token")
    app = FastAPI()
    app.include_router(
        build_run_router(event_stream=unused_stream, default_user_id="test")
    )
    with TestClient(app) as client:
        assert client.get("/run/agents").status_code == 401
        assert client.post("/run", json={"query": "hello"}).status_code == 401
        assert (
            client.get("/run/agents", headers={"X-Gateway-Token": "wrong"}).status_code
            == 401
        )
        response = client.get(
            "/run/agents", headers={"X-Gateway-Token": "harness-test-token"}
        )
        assert response.status_code == 200, response.text
