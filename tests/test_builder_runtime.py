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


def test_run_route_mount_requires_events_flag_and_auth(runtime, monkeypatch):
    from cuga.backend.server.run_routes import run_api_enabled

    for name in (
        "GATEWAY_TOKEN",
        "CUGA_SUPERVISOR_ROSTER",
        "CUGA_RUN_ALLOW_UNAUTHENTICATED",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CUGA_RUN_TOKEN", "harness-test-token")
    monkeypatch.delenv("CUGA_EVENTS_ENABLED", raising=False)
    assert not run_api_enabled()
    monkeypatch.setenv("CUGA_EVENTS_ENABLED", "true")
    assert run_api_enabled()
    monkeypatch.delenv("CUGA_RUN_TOKEN")
    assert not run_api_enabled()


@pytest.fixture
def scripted_model(runtime, monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langchain_core.runnables import RunnableLambda

    class ScriptedModel(FakeListChatModel):
        def _call(self, messages, **kwargs):
            text = "\n".join(str(m.content) for m in messages)
            last = str(messages[-1].content)
            if last.startswith("Execution output:"):
                return "Fixture execution completed: " + last
            if "delegate_to_crm" in text and "delegate_to_email" in text:
                return (
                    '```python\ncustomers = await delegate_to_crm(task="Get customers")\n'
                    'email = await delegate_to_email(task=f"Send a thank-you using {customers}")\n'
                    "print(customers)\nprint(email)\n```"
                )
            if "get_customers" in text:
                return "```python\ncustomers = await get_customers(limit=1)\nprint(customers)\n```"
            if "send_email" in text:
                contact = re.search(r"[\w.+-]+@[\w.-]+", last)
                record = re.search(r"CRM_RECORD_\w+", last)
                assert contact and record, "CRM output must reach the email agent"
                return (
                    f'```python\nmail = await send_email(to="{contact[0]}", '
                    f'body="Thank you for {record[0]}")\nprint(mail)\n```'
                )
            if "delete_record" in text:
                return '```python\ndeleted = await delete_record(record_id="fixture-1")\nprint(deleted)\n```'
            if "add_numbers" in text:
                return "```python\nresult = await add_numbers(a=5, b=3)\nprint(result)\n```"
            return "Fixture response."

        def with_structured_output(self, schema, **kwargs):
            assert schema["title"] == "SummaryResponse"
            return RunnableLambda(lambda messages: {"summary": "Fixture summary."})

    from cuga.backend.llm.models import LLMManager

    model = ScriptedModel(responses=["unused"])
    monkeypatch.setattr(LLMManager, "get_model", lambda *args, **kwargs: model)
    return model


def test_exact_sdk_single_and_supervisor_examples_execute(
    runtime, scripted_model, tmp_path, monkeypatch
):
    from cuga import CugaAgent, CugaSupervisor
    from cuga.backend.cuga_graph.policy.configurable import PolicyConfigurable
    from cuga.config import settings

    settings.set("advanced_features.reflection_enabled", False)
    settings.set("advanced_features.pre_execute_verify_enabled", False)
    settings.set("advanced_features.sandbox_mode", "local")
    calls = []

    # Run entire shipped coroutines; replace only provider/storage boundaries.
    async def check():
        storage = policy_storage(tmp_path)
        await storage.initialize_async()
        system = PolicyConfigurable(storage=storage, llm=scripted_model)

        def configured_agent(**kwargs):
            for tool in kwargs.get("tools", []):
                original = tool.func
                name = tool.name

                def audited(*args, _original=original, _name=name, **kw):
                    result = _original(*args, **kw)
                    calls.append((_name, kw, result))
                    return result

                tool.func = audited
            return CugaAgent(
                model=scripted_model,
                policy_system=system,
                auto_load_policies=False,
                filesystem_sync=False,
                **kwargs,
            )

        def configured_supervisor(**kwargs):
            return CugaSupervisor(
                model=scripted_model,
                policy_system=system,
                auto_load_policies=False,
                filesystem_sync=False,
                **kwargs,
            )

        try:
            for source in (
                blocks("build-agent", "python")
                + blocks("build-supervisor", "python")[:1]
            ):
                source = (
                    source.replace("from cuga import CugaAgent, CugaSupervisor\n", "")
                    .replace("from cuga import CugaAgent\n", "")
                    .replace("asyncio.run(main())", "")
                )
                ns = {
                    "CugaAgent": configured_agent,
                    "CugaSupervisor": configured_supervisor,
                }
                exec(source, ns)  # noqa: S102 - trusted shipped examples
                await ns["main"]()
            assert [x[0] for x in calls] == [
                "add_numbers",
                "get_customers",
                "send_email",
            ]
            assert calls[0][1] == {"a": 5, "b": 3}
            assert calls[0][2] == 8
            assert calls[1][1] == {"limit": 1}
            assert calls[2][1]["to"] == "alice@example.test"
            assert "CRM_RECORD_7" in calls[2][1]["body"]
        finally:
            await storage.disconnect()

    asyncio.run(check())


def test_documented_approval_pauses_accepts_and_denies(
    runtime, scripted_model, tmp_path
):
    from datetime import datetime
    from cuga import CugaAgent
    from cuga.backend.cuga_graph.policy.configurable import PolicyConfigurable
    from cuga.backend.cuga_graph.nodes.human_in_the_loop.followup_model import (
        ActionResponse,
        ActionType,
    )
    from langchain_core.tools import tool

    calls = []

    @tool
    def delete_record(record_id: str) -> str:
        """Delete a synthetic test record."""
        calls.append(record_id)
        return "FIXTURE_RECORD_DELETED"

    async def check():
        storage = policy_storage(tmp_path)
        await storage.initialize_async()
        system = PolicyConfigurable(storage=storage, llm=scripted_model)
        agent = CugaAgent(
            tools=[delete_record],
            model=scripted_model,
            policy_system=system,
            enable_knowledge=False,
            auto_load_policies=False,
            filesystem_sync=False,
        )
        folder = tmp_path / ".cuga" / "tool_approvals"
        folder.mkdir(parents=True)
        (folder / "delete.md").write_text(blocks("author-policy", "markdown")[3])
        try:
            loaded = await agent.policies.load_from_folder(str(folder.parent))
            assert loaded["count"] == 1 and not loaded["errors"]
            for confirmed in (True, False):
                calls.clear()
                thread = f"approval-{confirmed}"
                paused = await agent.invoke("Delete fixture record", thread_id=thread)
                assert not paused.error and not calls
                assert any(
                    d.outcome == "approval_required" for d in paused.policy_decisions
                )
                response = ActionResponse(
                    action_id="tool_approval",
                    response_type=ActionType.CONFIRMATION,
                    confirmed=confirmed,
                    timestamp=datetime.now().isoformat(),
                )
                resumed = await agent.invoke(
                    None,
                    thread_id=thread,
                    action_response=response,
                    track_tool_calls=True,
                )
                assert not resumed.error
                assert calls == (["fixture-1"] if confirmed else [])
                expected = "approved" if confirmed else "denied"
                assert any(d.outcome == expected for d in resumed.policy_decisions)
        finally:
            await agent.aclose()
            await storage.disconnect()

    asyncio.run(check())


def test_exact_formatter_template_produces_json(runtime, scripted_model, tmp_path):
    from cuga import CugaAgent
    from cuga.backend.cuga_graph.policy.configurable import PolicyConfigurable

    async def check():
        storage = policy_storage(tmp_path)
        await storage.initialize_async()
        system = PolicyConfigurable(storage=storage, llm=scripted_model)
        agent = CugaAgent(
            model=scripted_model,
            policy_system=system,
            enable_knowledge=False,
            auto_load_policies=False,
            filesystem_sync=False,
        )
        folder = tmp_path / ".cuga" / "output_formatters"
        folder.mkdir(parents=True)
        (folder / "summary.md").write_text(blocks("author-policy", "markdown")[4])
        try:
            loaded = await agent.policies.load_from_folder(str(folder.parent))
            assert loaded["count"] == 1 and not loaded["errors"]
            result = await agent.invoke("Give a summary")
            assert not result.error
            assert json.loads(result.answer) == {"summary": "Fixture summary."}
            assert any(
                d.policy_id == "formatter_summary" and d.outcome == "applied"
                for d in result.policy_decisions
            )
            other = await agent.invoke("Say hello", thread_id="no-formatter")
            assert not other.policy_decisions
        finally:
            await agent.aclose()
            await storage.disconnect()

    asyncio.run(check())


def test_managed_descriptions_and_openapi_dual_filter_contract(runtime):
    from cuga.backend.cuga_graph.nodes.cuga_lite.prompt_utils import (
        format_apps_for_prompt,
    )
    from cuga.backend.cuga_graph.nodes.cuga_lite.providers.base import AppDefinition
    from cuga.backend.cuga_graph.nodes.cuga_lite.providers.combined import (
        CombinedToolProvider,
    )
    from cuga.backend.tools_env.registry.config.config_loader import ServiceConfig
    from cuga.backend.tools_env.registry.mcp_manager.mcp_manager import MCPManager

    text = (SKILLS_DIR / "managed-server" / "SKILL.md").read_text()
    rows = re.findall(r"\| (?:MCP over HTTP|MCP subprocess|OpenAPI) \| `(.*?)`", text)
    entries = [json.loads(row) for row in rows]
    assert len(entries) == 3 and all(entry["description"] for entry in entries)
    apps = [
        AppDefinition(
            name=entry["name"],
            url=entry.get("url", ""),
            description=entry["description"],
        )
        for entry in entries
    ]
    assert format_apps_for_prompt(apps)
    assert "include" not in entries[2]
    schema = {"paths": {"/orders/{order_id}": {"get": {"operationId": "lookupOrder"}}}}
    manager = MCPManager({})
    provider = CombinedToolProvider()
    tool = SimpleNamespace(name="orders_lookuporder")
    # Registry uses case-sensitive operationId; agent uses the callable name.
    by_operation = ServiceConfig(include=["lookupOrder"])
    assert manager._filter_and_override_schema(schema, by_operation)["paths"]
    assert not provider._filter_tools_by_include([tool], "orders", by_operation.include)
    by_callable = ServiceConfig(include=[tool.name])
    assert not manager._filter_and_override_schema(schema, by_callable)["paths"]
    assert provider._filter_tools_by_include([tool], "orders", by_callable.include) == [
        tool
    ]


def test_managed_supervisor_demo_seed_creates_specialists_and_published_refs(runtime):
    from cuga.backend.server.config_store import load_config, load_draft
    from cuga.backend.server.demo_manage_setup import _seed_supervisor_demo_config_async

    async def check():
        await _seed_supervisor_demo_config_async()
        supervisor, version = await load_config(None, "team-supervisor")
        assert version.isdigit()
        assert supervisor["agent"]["kind"] == "supervisor"
        refs = [entry["ref"] for entry in supervisor["supervisor"]["subAgents"]]
        assert refs == ["crm-agent", "email-agent", "filesystem-agent"]
        for agent_id in [*refs, "team-supervisor"]:
            draft = await load_draft(agent_id)
            published, version = await load_config(None, agent_id)
            assert draft["agent"] == published["agent"]
            assert version.isdigit()
        filesystem, _ = await load_config(None, "filesystem-agent")
        assert filesystem["advanced_features"]["enable_filesystem_tools"] is True

    asyncio.run(check())
