"""Opt-in, isolated full server checks with a scripted HTTP model/embeddings.

CUGA_NETWORK_TESTS=1; run with a CUGA Python environment. Never connects to an
operator's server or uses real provider credentials. Not a reasoning-quality eval.
"""

import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time

import pytest

from cuga_harness_kit.cli import SKILLS_DIR

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("CUGA_NETWORK_TESTS") != "1", reason="opt-in local CUGA services"
    ),
]
FIXTURES = Path(__file__).parent / "fixtures"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def checked(response):
    response.raise_for_status()
    data = response.json()
    assert data.get("status") not in ("error", "partial"), data
    assert not data.get("tool_errors") and not data.get("policy_errors"), data
    return data


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    import httpx

    root = tmp_path_factory.mktemp("cuga-network")
    model_port, mcp_port, registry_port, server_port = [free_port() for _ in range(4)]
    model_base = f"http://127.0.0.1:{model_port}"
    registry_base = f"http://127.0.0.1:{registry_port}"
    base = f"http://127.0.0.1:{server_port}"
    # Preserve interpreter paths only; operator credentials, Dynaconf/provider
    # overrides, proxy settings, and config paths must not cross this boundary.
    allowed = {"PATH", "PYTHONPATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    empty = root / "empty.env"
    empty.touch()
    env.update(
        {
            "ENV_FILE": str(empty),
            "ENV_FILE_PATH": str(empty),
            "AGENT_SETTING_CONFIG": "settings.openai.toml",
            "OPENAI_API_KEY": "local-test-only",
            "OPENAI_BASE_URL": model_base + "/v1",
            "MODEL_NAME": "fixture",
            "CUGA_DBS_DIR": str(root / "dbs"),
            "CUGA_LOGGING_DIR": str(root / "logs"),
            "MAC_USER_DATA_PATH": str(root / "logs"),
            "DYNACONF_STORAGE__LOCAL_DB_PATH": str(root / "dbs" / "cuga.db"),
            "DYNACONF_STORAGE__MODE": "local",
            "DYNACONF_STORAGE__EMBEDDING__PROVIDER": "openai",
            "DYNACONF_STORAGE__EMBEDDING__MODEL": "text-embedding-3-small",
            "DYNACONF_STORAGE__EMBEDDING__BASE_URL": model_base + "/v1",
            "DYNACONF_STORAGE__EMBEDDING__API_KEY": "local-test-only",
            "DYNACONF_STORAGE__EMBEDDING__DIM": "1536",
            "DYNACONF_KNOWLEDGE__ENABLED": "false",
            "DYNACONF_KNOWLEDGE__EMBEDDINGS__PROVIDER": "openai",
            "DYNACONF_KNOWLEDGE__EMBEDDINGS__BASE_URL": model_base + "/v1",
            "DYNACONF_KNOWLEDGE__EMBEDDINGS__API_KEY": "local-test-only",
            "DYNACONF_POLICY__FILESYSTEM_SYNC": "false",
            "DYNACONF_POLICY__AUTO_LOAD_POLICIES": "false",
            "DYNACONF_ADVANCED_FEATURES__LANGFUSE_TRACING": "false",
            "DYNACONF_OBSERVABILITY__ENABLED": "false",
            "DYNACONF_ADVANCED_FEATURES__MODE": "api",
            "DYNACONF_ADVANCED_FEATURES__SANDBOX_MODE": "local",
            "DYNACONF_ADVANCED_FEATURES__REFLECTION_ENABLED": "false",
            "DYNACONF_ADVANCED_FEATURES__PRE_EXECUTE_VERIFY_ENABLED": "false",
            "DYNACONF_ADVANCED_FEATURES__ENABLE_TODOS": "false",
            "DYNACONF_ADVANCED_FEATURES__ENABLE_FILESYSTEM_TOOLS": "false",
            "DYNACONF_ADVANCED_FEATURES__TRACKER_ENABLED": "true",
            "DYNACONF_EVOLVE__ENABLED": "false",
            "DYNACONF_SERVER_PORTS__DEMO": str(server_port),
            "DYNACONF_SERVER_PORTS__REGISTRY": str(registry_port),
            "DYNACONF_SERVER_PORTS__REGISTRY_HOST": registry_base,
            "DYNACONF_AUTH__ENABLED": "false",
            "DYNACONF_SUPERVISOR__REGISTRY_ENABLED": "true",
            "DYNACONF_SECRETS__FORCE_ENV": "false",
            "MCP_SERVERS_FILE": "none",
            "CUGA_TEST_ENV": "true",
            "CUGA_MANAGER_MODE": "true",
            "CUGA_EVENTS_ENABLED": "true",
            "CUGA_RUN_TOKEN": "local-fixture-run-token",
            "CUGA_FIXTURE_PORT": str(model_port),
            "CUGA_MCP_FIXTURE_PORT": str(mcp_port),
            "CUGA_FIXTURE_LOG_DIR": str(root),
            "CUGA_BASE_URL": base,
        }
    )
    # Do not accidentally enable a preloaded supervisor or external event service.
    for key in (
        "CUGA_SUPERVISOR_ROSTER",
        "CUGA_EVENTS_API_URL",
        "CUGA_RUN_ALLOW_UNAUTHENTICATED",
    ):
        env.pop(key, None)
    for folder in ("dbs", "logs"):
        (root / folder).mkdir()
    processes = []
    logs = []

    def launch(label, args, url, accept_405=False):
        log = (root / f"{label}.log").open("w")
        logs.append(log)
        proc = subprocess.Popen(
            [sys.executable, *args],
            cwd=root,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        processes.append(proc)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            assert proc.poll() is None, (root / f"{label}.log").read_text()[-6000:]
            try:
                response = httpx.get(url, timeout=1)
                if response.status_code == 200 or (
                    accept_405 and response.status_code in (405, 406)
                ):
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        pytest.fail(
            f"{label} did not become ready: {(root / f'{label}.log').read_text()[-6000:]}"
        )

    try:
        launch(
            "http-fixture", [str(FIXTURES / "http_service.py")], model_base + "/audit"
        )
        launch(
            "mcp-fixture",
            [str(FIXTURES / "mcp_service.py"), "--http"],
            f"http://127.0.0.1:{mcp_port}/mcp",
            True,
        )
        launch(
            "registry",
            ["-m", "cuga.backend.tools_env.registry.registry.api_registry_server"],
            registry_base + "/status",
        )
        launch(
            "server",
            [
                "-m",
                "uvicorn",
                "cuga.backend.server.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(server_port),
            ],
            base + "/openapi.json",
        )
        with httpx.Client(
            base_url=base,
            headers={"X-Gateway-Token": env["CUGA_RUN_TOKEN"]},
            timeout=120,
        ) as client:
            yield {
                "root": root,
                "env": env,
                "client": client,
                "registry": registry_base,
                "model": model_base,
                "mcp_port": mcp_port,
            }
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
        for log in logs:
            log.close()


def config(stack):
    return {
        "agent": {"name": "Harness Network Agent"},
        "knowledge": {"enabled": False},
        "llm": {
            "provider": "openai",
            "model": "fixture",
            "base_url": stack["model"] + "/v1",
            "api_key": "local-test-only",
        },
        "tools": [],
        "policies": {"policies": []},
    }


def test_exact_managed_http_example_on_launched_server(stack):
    client = stack["client"]
    assert "/run" in client.get("/openapi.json").json()["paths"]
    assert (
        client.get("/run/agents", headers={"X-Gateway-Token": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            "/run", headers={"X-Gateway-Token": ""}, json={"query": "hi"}
        ).status_code
        == 401
    )
    path = stack["root"] / "config.json"
    path.write_text(json.dumps(config(stack)))
    source = re.findall(
        r"^```python\n(.*?)^```",
        (SKILLS_DIR / "managed-server" / "SKILL.md").read_text(),
        re.MULTILINE | re.DOTALL,
    )[0]
    env = {**stack["env"], "CUGA_CONFIG_FILE": str(path)}
    run = subprocess.run(
        [sys.executable, "-c", source],
        env=env,
        cwd=stack["root"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "Hello from the fixture model." in run.stdout


def test_managed_mcp_http_stdio_and_openapi_execute_before_and_after_publish(stack):
    import httpx

    cfg = config(stack)
    # Parse actual documented tool shapes rather than maintaining duplicate schemas.
    text = (SKILLS_DIR / "managed-server" / "SKILL.md").read_text()
    rows = re.findall(r"\| (?:MCP over HTTP|MCP subprocess|OpenAPI) \| `(.*?)`", text)
    tools = [json.loads(row) for row in rows]
    assert len(tools) == 3
    for tool, name in zip(tools, ("orders_http", "orders_stdio", "orders_api")):
        tool["name"] = name
        assert tool["description"]
    tools[0]["url"] = f"http://127.0.0.1:{stack['mcp_port']}/mcp"
    tools[1].update(
        command=sys.executable,
        args=[
            str(FIXTURES / "mcp_service.py"),
            "--stdio",
            "--log-dir",
            str(stack["root"]),
        ],
        cwd=str(stack["root"]),
    )
    tools[2]["url"] = stack["model"] + "/openapi.json"
    cfg["tools"] = tools
    params = {"agent_id": "cuga-default"}
    before = httpx.get(stack["model"] + "/audit").json().get("openapi_calls", 0)
    for draft in (True, False):
        if not draft:
            # Original MCP names that also match agent callable suffixes.
            tools[0]["include"] = ["lookup_order"]
            tools[1]["include"] = ["lookup_order"]
        path = "/api/manage/config/draft" if draft else "/api/manage/config"
        checked(stack["client"].post(path, params=params, json={"config": cfg}))
        registry_id = "cuga-default--draft" if draft else "cuga-default"
        apis = httpx.get(
            stack["registry"] + "/apis", params={"agent_id": registry_id}, timeout=30
        ).json()
        for app in ("orders_http", "orders_stdio", "orders_api"):
            tool = next(
                name
                for name, schema in apis[app].items()
                if schema.get("operation_id") == "lookupOrder" or "lookup_order" in name
            )
            result = checked(
                stack["client"].post(
                    "/run",
                    json={
                        "query": f"Look up order H123 using {tool}.",
                        "use_draft": draft,
                        "thread_id": f"{app}-{draft}",
                    },
                )
            )
            marker = "OPENAPI_EXECUTED" if app == "orders_api" else "MCP_EXECUTED"
            assert result["ok"] and marker in result["answer"], result
            assert result["variables"], result
    assert httpx.get(stack["model"] + "/audit").json()["openapi_calls"] == before + 2
    calls = [
        json.loads(line)
        for line in (stack["root"] / "mcp-calls.jsonl").read_text().splitlines()
    ]
    assert [c["transport"] for c in calls].count("--http") == 2
    assert [c["transport"] for c in calls].count("--stdio") == 2
    assert all(c["order_id"] == "H123" for c in calls)


@pytest.fixture(scope="module")
def knowledge_result(stack):
    root = stack["root"] / "knowledge-worker"
    root.mkdir()
    env = {
        **stack["env"],
        "DYNACONF_KNOWLEDGE__ENABLED": "true",
        "DYNACONF_KNOWLEDGE__AGENT_LEVEL_ENABLED": "true",
        "DYNACONF_KNOWLEDGE__SESSION_LEVEL_ENABLED": "true",
        "DYNACONF_KNOWLEDGE__RAG_PROFILE": "speed",
        "CUGA_KNOWLEDGE_WORKER_DIR": str(root),
        "CUGA_DBS_DIR": str(root / "dbs"),
        "CUGA_LOGGING_DIR": str(root / "logs"),
        "DYNACONF_STORAGE__LOCAL_DB_PATH": str(root / "sdk.db"),
    }
    log = root / "worker.log"
    with log.open("w") as output:
        run = subprocess.run(
            [sys.executable, str(FIXTURES / "knowledge_worker.py")],
            cwd=root,
            env=env,
            stdout=output,
            stderr=output,
            timeout=120,
        )
    assert run.returncode == 0, log.read_text()[-6000:]
    return json.loads((root / "result.json").read_text())


def test_knowledge_ingestion_search_and_session_isolation(knowledge_result):
    data = knowledge_result
    assert (
        data["ingestion"]["status"] == "completed"
        and not data["ingestion"]["failed_files"]
    )
    assert any("42 million" in result["text"] for result in data["results"])
    assert data["docs"][0]["status"] == "indexed"
    assert len(data["first"]) == 1 and data["other"] == []


@pytest.mark.parametrize("valid_endpoint", [True, False])
def test_using_cuga_model_check_executes_configured_request(stack, valid_endpoint):
    source = (SKILLS_DIR / "using-cuga" / "SKILL.md").read_text()
    examples = re.findall(r"^```python\n(.*?)^```", source, re.MULTILINE | re.DOTALL)
    assert len(examples) == 1
    env = dict(stack["env"])
    if not valid_endpoint:
        env["OPENAI_BASE_URL"] = stack["model"] + "/missing/v1"
    run = subprocess.run(
        [sys.executable, "-c", examples[0]],
        cwd=stack["root"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if valid_endpoint:
        assert run.returncode == 0, run.stderr[-6000:]
        assert "Configured LLM request succeeded" in run.stdout
        requests = [
            json.loads(line)
            for line in (stack["root"] / "model-requests.jsonl")
            .read_text()
            .splitlines()
        ]
        assert any(
            r["model"] == "fixture"
            and r["messages"][-1]["content"] == "Reply with a short greeting."
            for r in requests
        )
    else:
        assert run.returncode != 0
        assert "404" in run.stderr
        assert "Configured LLM request succeeded" not in run.stdout
    assert env["OPENAI_API_KEY"] not in run.stdout + run.stderr


class AutomaticRagRuntimeFailure(AssertionError):
    pass


@pytest.mark.xfail(
    strict=True,
    raises=AutomaticRagRuntimeFailure,
    reason="CUGA v0.4.0 injects thread_id rejected by the knowledge tool argument validator",
)
def test_automatic_rag_tool_execution_and_citations(knowledge_result):
    answer = knowledge_result["answer"]
    assert not answer["error"], answer
    errors = [call.get("error") for call in answer["tool_calls"] if call.get("error")]
    if "Unexpected argument(s) for knowledge_search_knowledge: thread_id" in errors:
        raise AutomaticRagRuntimeFailure(errors)
    assert not errors, errors
    assert answer["sources"] and "42 million" in answer["answer"], answer
    assert answer["sources"][0]["filename"] == "quarterly_report.txt"


def test_managed_supervisor_delegates_and_keeps_draft_out_of_production(stack):
    text = (SKILLS_DIR / "build-supervisor" / "SKILL.md").read_text()
    configs = [
        json.loads(row)
        for row in re.findall(r"^```json\n(.*?)^```", text, re.MULTILINE | re.DOTALL)
    ]
    assert len(configs) == 3
    client = stack["client"]
    ids = []
    for cfg in configs:
        created = checked(client.post("/api/agents", json=cfg["agent"]))
        ids.append(created["id"])
        if cfg["agent"]["kind"] == "single":
            cfg["tools"][0]["url"] = f"http://127.0.0.1:{stack['mcp_port']}/mcp"
            cfg["llm"] = config(stack)["llm"]
        checked(
            client.post(
                "/api/manage/config/draft",
                params={"agent_id": created["id"]},
                json={"config": cfg},
            )
        )
    assert [entry["ref"] for entry in configs[2]["supervisor"]["subAgents"]] == ids[:2]
    source = re.findall(r"^```python\n(.*?)^```", text, re.MULTILINE | re.DOTALL)[1]

    def invoke(draft, expected_marker):
        calls_path = stack["root"] / "supervisor-calls.jsonl"
        before = calls_path.read_text().splitlines() if calls_path.exists() else []
        run = subprocess.run(
            [sys.executable, "-c", source],
            cwd=stack["root"],
            env={
                **stack["env"],
                "CUGA_SUPERVISOR_ID": ids[2],
                "CUGA_USE_DRAFT": str(draft).lower(),
            },
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stdout[-4000:] + run.stderr[-4000:]
        after = calls_path.read_text().splitlines() if calls_path.exists() else []
        calls = [json.loads(line) for line in after[len(before) :]]
        assert [call["tool"] for call in calls] == ["get_customers", "send_email"], (
            run.stdout[-6000:]
        )
        assert calls[0]["limit"] == 1
        assert calls[1]["to"] == calls[0]["contact"]
        assert calls[0]["record"] in calls[1]["body"]
        assert expected_marker in calls[1]["body"]
        assert "EMAIL_EXECUTED" in run.stdout
        assert "event: Answer" in run.stdout
        assert "event: Error" not in run.stdout

    # A newly created named draft reads the published tool catalog in v0.4.0.
    # Probe this explicitly so the skill cannot promise draft-only tool execution.
    prepublish = subprocess.run(
        [sys.executable, "-c", source],
        cwd=stack["root"],
        env={**stack["env"], "CUGA_SUPERVISOR_ID": ids[0], "CUGA_USE_DRAFT": "true"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert prepublish.returncode == 0, prepublish.stderr[-4000:]
    assert "event: Answer" in prepublish.stdout
    assert not (stack["root"] / "supervisor-calls.jsonl").exists()
    # Publish specialists before composing the production team.
    for agent_id, cfg in zip(ids[:2], configs[:2]):
        checked(
            client.post(
                "/api/manage/config",
                params={"agent_id": agent_id},
                json={"config": cfg},
            )
        )
    import httpx

    # The first draft invocation cached an empty published CRM catalog.
    stale = httpx.get(
        stack["registry"] + "/apis", params={"agent_id": ids[0]}, timeout=30
    )
    stale.raise_for_status()
    assert "crm_tools" not in stale.json()
    checked(
        httpx.post(
            stack["registry"] + "/reload", params={"agent_id": ids[0]}, timeout=30
        )
    )
    refreshed = httpx.get(
        stack["registry"] + "/apis", params={"agent_id": ids[0]}, timeout=30
    )
    refreshed.raise_for_status()
    assert any("get_customers" in name for name in refreshed.json()["crm_tools"])
    invoke(True, "EMAIL_PUBLISHED")
    published = checked(
        client.post(
            "/api/manage/config",
            params={"agent_id": ids[2]},
            json={"config": configs[2]},
        )
    )
    assert published["version"].isdigit()
    invoke(False, "EMAIL_PUBLISHED")
    # Change a specialist draft while keeping production intact.
    configs[1]["special_instructions"] += " Include EMAIL_DRAFT in the email body."
    checked(
        client.post(
            "/api/manage/config/draft",
            params={"agent_id": ids[1]},
            json={"config": configs[1]},
        )
    )
    invoke(True, "EMAIL_DRAFT")
    invoke(False, "EMAIL_PUBLISHED")
    checked(
        client.post(
            "/api/manage/config",
            params={"agent_id": ids[1]},
            json={"config": configs[1]},
        )
    )
    invoke(False, "EMAIL_DRAFT")
    # The exact skill client must reject disabled named routing before invocation.
    disabled = subprocess.run(
        [sys.executable, "-c", source],
        cwd=stack["root"],
        env={
            **stack["env"],
            "CUGA_BASE_URL": stack["model"],
            "CUGA_SUPERVISOR_ID": ids[2],
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert disabled.returncode != 0
    assert "refusing default-agent fallback" in disabled.stderr

    assert (
        httpx.get(stack["model"] + "/audit").json().get("unexpected_stream_calls", 0)
        == 0
    )
    # Unknown named routing must fail rather than execute the default agent.
    response = client.post(
        "/stream", headers={"X-Agent-ID": "missing-team"}, json={"query": "hi"}
    )
    assert response.status_code == 404
