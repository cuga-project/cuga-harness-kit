---
name: cuga-managed-server
description: Use when the user wants a managed CUGA server, Manage UI, draft testing, published/versioned agent config, HTTP invocation, or to deploy tools/policies/knowledge without embedding the Python SDK.
---

# Building with the managed server

The managed server has a separate draft and published config per agent. SDK construction does not update these. For a new build, use `using-cuga` to establish LLM readiness and the user's goal/mode first; reuse an existing verified setup. A custom frontend can call this server over HTTP. When integrating with an existing published agent, keep its stored config and use the HTTP invocation/agent selection instructions below; local SDK installation, Manage access and publishing are unnecessary for a client-only integration. Keep provider credentials on the server. Start a new local server with `cuga-install-and-launch`, then:

```bash
uv run cuga start manager
```

Use the URL printed by the launcher (normally `http://localhost:7860`; SSL configuration may enable HTTPS). Open Manage, configure the agent name, LLM, tools, policies, and knowledge, test in draft chat, then Publish. Production chat uses the published version. Manager stores configuration in its config database and generates managed registry YAML; do not edit the installed package's YAML or `.cuga/` policy files to update it.

For multiple specialists coordinated by a named supervisor, follow `cuga-build-supervisor` for agent creation, internal ID references, draft/production behavior and delegation checks.

## HTTP configuration workflow

The following example operates on `cuga-default`. For named agents, first create/select one through Manage and keep the same `agent_id` on every config request. Inspect the current config before editing. For an existing server, prefer section PATCH requests for draft edits. GET responses redact credentials and cannot be used as a complete publish payload. Manage endpoints require a session/token with manage access when authentication is enabled; pass the configured credential via `CUGA_AUTH_TOKEN`. Do not invent an auth route or put secrets in committed config files.

This example deploys a complete config from an authoritative local JSON file specified by `CUGA_CONFIG_FILE`. Prepare that file with the intended agent, LLM, tools, policies and knowledge settings; use server-supported credential references or environment-backed provider credentials. Do not derive it by copying a redacted GET response. Keep files containing secrets out of Git. It requires a running server and an LLM for the smoke query. `/run` is opt-in: set `CUGA_EVENTS_ENABLED=true` on the server before launching it, along with `CUGA_RUN_TOKEN` (or `GATEWAY_TOKEN`). The token alone does not mount the route. Restart the server after changing these variables, then check that `/openapi.json` advertises `/run`; an HTML fallback or HTTP 200 from `/run/agents` does not prove it is mounted. `/run` separately requires `X-Gateway-Token` matching `CUGA_RUN_TOKEN` (or `GATEWAY_TOKEN`) on the server, or an authenticated chat JWT; set the same shared token on the client before running even when local UI authentication is disabled.

```python
import json
import os
from pathlib import Path
import httpx

base = os.getenv("CUGA_BASE_URL", "http://localhost:7860").rstrip("/")
agent_id = "cuga-default"
headers = {}
run_token = os.getenv("CUGA_RUN_TOKEN") or os.getenv("GATEWAY_TOKEN")
if run_token:
    headers["X-Gateway-Token"] = run_token
if not run_token and not os.getenv("CUGA_AUTH_TOKEN"):
    raise RuntimeError("Set CUGA_RUN_TOKEN to match the server, or provide an authenticated chat JWT")
if os.getenv("CUGA_AUTH_TOKEN"):
    headers["Authorization"] = "Bearer " + os.environ["CUGA_AUTH_TOKEN"]

with httpx.Client(base_url=base, headers=headers, timeout=120) as client:
    params = {"agent_id": agent_id}
    def checked(response):
        response.raise_for_status()
        data = response.json()
        if data.get("status") in ("partial", "error") or data.get("policy_errors") or data.get("tool_errors"):
            raise RuntimeError(data)
        return data

    checked(client.get("/api/manage/config", params={**params, "draft": "1"}))  # inspect only: secrets are redacted
    config = json.loads(Path(os.environ["CUGA_CONFIG_FILE"]).read_text())
    if not config.get("agent", {}).get("name"):
        raise ValueError("The full config requires agent.name")
    checked(client.post("/api/manage/config/draft", params=params, json={"config": config}))

    # /run's explicit draft selector below is for cuga-default.
    draft = checked(client.post("/run", json={
        "query": "Reply with a short greeting", "use_draft": True,
        "thread_id": "harness-draft-smoke",
    }))
    assert draft.get("ok") and draft["status"] == "ok", draft
    assert draft["answer"], draft

    published = checked(client.post("/api/manage/config", params=params, json={"config": config}))
    assert published["version"].isdigit(), published
    saved = checked(client.get("/api/manage/config", params=params))
    assert saved["version"] == published["version"], saved
    assert saved["config"]["agent"]["name"] == config["agent"]["name"], saved

    production = checked(client.post("/run", json={
        "query": "Reply with a short greeting", "thread_id": "harness-production-smoke",
    }))
    assert production.get("ok") and production["status"] == "ok", production
    assert production["answer"], production
    print(published["version"], production["answer"])
```

Publish is `POST /api/manage/config`, not `/config/publish`. The body is `{"config": <full config>}`; an agent name is required. `POST /api/manage/config/draft` replaces the full draft. Section edits use `PATCH /api/manage/config/draft/<section>` (e.g. `tools`, `policies`, `llm`) with `{"<section>": ...}`. Draft save does not publish. The config GET redacts secrets. Never POST that redacted object back as a full replacement: blank keys can erase stored credentials. A name-only edit should PATCH the `agent` section; publishing still needs the complete authoritative config. Supply credentials through supported server references/environment or a trusted full config source.

## Tools and policies in config

| Item | Managed shape |
|---|---|
| MCP over HTTP | `{"name": "orders", "description": "Order lookup tools", "type": "mcp", "url": "http://localhost:9000/mcp", "transport": "http"}` in `config.tools` |
| MCP subprocess | `{"name": "orders", "description": "Order lookup tools", "type": "mcp", "command": "uv", "args": ["run", "python", "orders_server.py"], "transport": "stdio", "cwd": "/absolute/project/path"}` |
| OpenAPI | `{"name": "orders", "description": "Order service", "type": "openapi", "url": "http://localhost:9000/openapi.json"}` |
| Python function | Use an SDK LangChain tool, or expose it as MCP/OpenAPI for the managed server |
| Policies | Serialized policy objects under `config.policies` (list, or `{"policies": [...]}`); file frontmatter is not the JSON schema |

Supply a nonempty `description` for every managed tool entry. In the reviewed CUGA version, discovery succeeds without one but agent prompt construction fails on `description: null`. Discover callable names from the registry: MCP tools are prefixed with the app name, and OpenAPI callable names can differ from `operation_id`. For MCP, the registry filters `include` against original server tool names before prefixing/sanitizing, while the agent filters callable names/suffixes. A compatible original name such as `lookup_order` can work at both layers; the full `orders_lookup_order` name fails registry filtering. If sanitization makes the original name differ from the callable suffix, omit `include` and restrict the server instead. Verify discovery and execution after saving. For OpenAPI in v0.4.0, omit `include` in the example: the registry filters by exact operation IDs while the agent provider filters the same list by callable names. When those names differ, tools disappear at one of the two layers. Use an API/MCP service exposing only the intended operations when you need restricted exposure; do not claim an `include` list works without checking both discovery and execution.

A serialized keyword guard looks like this; save it into the policies section of the full config and test `delete all records` before publishing:

```json
{
  "id": "guard_delete", "name": "Block Delete Operations", "type": "intent_guard",
  "description": "Prevents deletion of critical data",
  "enabled": true, "priority": 100,
  "triggers": [{"type": "keyword", "value": ["delete", "remove"], "target": "intent", "operator": "or", "case_sensitive": false}],
  "response": {"response_type": "natural_language", "content": "Deletion operations are not permitted for security reasons."},
  "allow_override": false
}
```

Registry reload may return `partial` with `tool_errors` even on HTTP 200. Require actual tool discovery and a successful tool call. Verify the resulting production behavior after publish; never report a tool as working just because the config was saved.

## Invocation and isolation

For the `/run` example, supply `CUGA_RUN_TOKEN` through the server environment, then launch with `CUGA_EVENTS_ENABLED=true uv run cuga start manager`. Use the same token on the client. UI draft chat and `/stream` do not require enabling the events routes.

`POST /run` takes `query`, optional `thread_id`, and optional `agent` selection. It returns `ok`, `status` (`ok`, `error`, or `interrupt`), `answer`, `thread_id`, `sources`, `variables`, and `error`. HTTP 200 alone is not success. Reuse the returned `thread_id` for a conversation and approval resume; use a separate thread when comparing draft and production.

`GET /run/agents` lists available agents. In the reviewed CUGA version, `/run` does not route arbitrary managed agent IDs: `agent` only adds advisory sub-agent guidance in preloaded-supervisor mode. For named managed agents use `/stream` with `X-Agent-ID: <id>`; add `X-Use-Draft: true` for draft testing and omit it for published-agent invocation. Alternatively use the selected agent's Manage chat when you have manage access. Named routing requires the agent registry feature to be enabled. The `use_draft` example above selects the shared default draft. Check the installed version's `/openapi.json`, `run_routes.py` and stream handler before assuming selector behavior.

## Knowledge and deployment checks

Configure managed knowledge through Manage or supported `cuga knowledge` server commands (`--help` shows current options). SDK `agent.knowledge` belongs to the SDK process. Session uploads attach to the same server `thread_id` used for invocation; agent documents attach to the selected agent. Verify ingestion status, retrieval, and citations. Publish snapshots configuration, not a portable copy of every document or credential; inspect export/import support for deployment.

Before reporting completion, record the CUGA version when available, selected agent ID, successful production query, and tool/policy checks relevant to the requested integration. When changing managed config, also record the published version and draft/production checks. A client-only integration does not need Manage access to inspect or republish config. Distinguish configuration/storage checks from live LLM/tool/RAG checks. If credentials or services are unavailable, report exactly which checks ran and which did not.
