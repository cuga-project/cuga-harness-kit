---
name: cuga-build-supervisor
description: Use when building or customizing a multi-agent CUGA supervisor, composing specialist agents through the SDK or Manage, or working with demo_supervisor and manager --seed-supervisor-demo.
---

# Building a CUGA supervisor

Use `using-cuga` for a new build's LLM readiness, tracker setup and SDK/server choice; reuse an established setup. A supervisor coordinates specialist agents within the selected execution path. Identify each specialist's responsibility, tools, inputs and outputs. Use distinct descriptions and stable names/IDs, and check that the supervisor's model and every specialist's model work. Do not configure a managed server by constructing SDK objects.

## Embedded SDK

The example uses environment model defaults. If the application already supplies a verified `model=` instance, pass that instance to the specialists and supervisor instead of changing providers; preserve distinct verified models when the roles use different ones.

```python
from cuga import CugaAgent, CugaSupervisor
from langchain_core.tools import tool
import asyncio

@tool
def get_customers(limit: int = 10) -> str:
    """Fetch top customers from CRM."""
    return "Alice <alice@example.test>; customer record CRM_RECORD_7"

@tool
def send_email(to: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"

async def main():
    crm_agent = CugaAgent(tools=[get_customers], enable_knowledge=False)
    crm_agent.description = "CRM and customer data"

    email_agent = CugaAgent(tools=[send_email], enable_knowledge=False)
    email_agent.description = "Sending emails and notifications"

    supervisor = CugaSupervisor(agents={"crm": crm_agent, "email": email_agent})
    try:
        result = await supervisor.invoke("Get our top customer from CRM, then pass the returned contact and customer record to the email agent to send a thank-you")
        if result.error:
            raise RuntimeError(result.error)
        print(result.answer)
    finally:
        await supervisor.aclose()
        await crm_agent.aclose()
        await email_agent.aclose()

asyncio.run(main())
```

Each sub-agent needs a `.description`; the supervisor uses it to decide who handles what. In generated multi-step plans, the delegation tools can forward structured existing values with `variables=["customer_data"]`.

The example tools are local fixtures: `send_email` returns a string without sending real mail. Replace them with the user's integrations through `cuga-build-tool`. Verify the CRM tool runs, its returned contact reaches the email agent, and the email tool receives that contact; a narrated success is insufficient. Use a stable `thread_id` for a conversation and different threads for separate validation runs. Read `cuga-author-policy` when approvals or other policies are needed. `await CugaSupervisor.from_yaml("team.yaml")` is an alternative for SDK construction; SDK/YAML configuration does not publish managed config. In the reviewed v0.4.0 runtime, the YAML supervisor `model` block is not applied by `from_yaml` or the demo graph loader: the supervisor uses runtime defaults, while specialist model overrides are applied. Check effective models against the installed version.

## Managed server: named agents and a supervisor

Use `cuga-managed-server` for credentials, authoritative config files, config save/publish semantics and tool shapes. For a new local team, enable `DYNACONF_SUPERVISOR__REGISTRY_ENABLED=true` in the server's `.env` and launch `uv run --env-file .env cuga start manager`. For an existing remote server, verify `GET /api/ui/config` reports `agent_registry: true`, then list IDs with `GET /api/agents`; the list endpoint alone can return HTTP 200 with only `cuga-default` while the registry is disabled. With the flag off, `/stream` ignores a named selector and runs the default agent. Do not require a local SDK or modify the server just to invoke a published team. Reuse a running local server; before restarting one with saved configs, verify `storage.preserve_configs_on_startup` (for example `DYNACONF_STORAGE__PRESERVE_CONFIGS_ON_STARTUP=any`) so the local manager startup does not reset its config store.

1. List agents through Manage or `GET /api/agents`. Create each specialist with `POST /api/agents`, e.g. `{"name":"CRM Agent","description":"Looks up customer contacts","kind":"single"}`. Create the coordinator with `kind: "supervisor"`. Keep each returned `id`; do not assume IDs from display names. Reuse an existing agent only when it is the intended agent, and inspect its config before editing.
2. Save each specialist's complete authoritative config with `POST /api/manage/config/draft?agent_id=<id>` and `{"config": <config>}`. Configure its own provider/model (or verified server environment defaults), tools and policies. Check saved configuration and provider readiness; see the published-registry dependency in step 4 before expecting a new named draft to execute its tools. The following examples assume IDs `crm-agent`, `email-agent` and `team-supervisor`; substitute the returned IDs and actual service URLs. These MCP services must expose `get_customers` and `send_email` respectively. Keep their app descriptions nonempty and verify callable names after discovery.

```json
{
  "agent": {"name": "CRM Agent", "description": "Looks up customer contacts", "kind": "single"},
  "knowledge": {"enabled": false},
  "special_instructions": "Retrieve the requested customer using the CRM tools and return the contact and customer record unchanged.",
  "tools": [{"name": "crm_tools", "description": "Customer contact lookup", "type": "mcp", "url": "http://localhost:9000/mcp", "transport": "http", "include": ["get_customers"]}],
  "policies": {"policies": []}
}
```

```json
{
  "agent": {"name": "Email Agent", "description": "Sends email using the supplied customer contact", "kind": "single"},
  "knowledge": {"enabled": false},
  "special_instructions": "Send a thank-you using the contact and customer record supplied in the delegated task. Use the email tool; do not invent a recipient.",
  "tools": [{"name": "email_tools", "description": "Email delivery", "type": "mcp", "url": "http://localhost:9001/mcp", "transport": "http", "include": ["send_email"]}],
  "policies": {"policies": []}
}
```

3. Save the supervisor draft with internal references to the specialist IDs:

```json
{
  "agent": {"name": "Team Supervisor", "description": "Coordinates CRM lookup and email delivery", "kind": "supervisor"},
  "special_instructions": "Delegate CRM lookup first, then pass the returned contact and customer record to the email agent. Report tool failures instead of claiming completion.",
  "supervisor": {"subAgents": [{"kind": "internal", "ref": "crm-agent"}, {"kind": "internal", "ref": "email-agent"}], "planApproval": false},
  "policies": {"policies": []}
}
```

The supervisor uses verified server model defaults when no explicit nonempty `llm.model` is stored. Configure its model explicitly in the authoritative JSON if a different model is needed. `planApproval: false` avoids a plan-approval pause in this example; honor the user's approval requirements in their application.

4. Provision and verify the specialist tool catalogs. In the reviewed v0.4.0 runtime, both named single-agent drafts and stored supervisor specialists use a published registry ID for tools. A draft-only agent can answer without its tools. For a new team, use isolated test agents/services: review the drafts, publish each specialist's authoritative config to provision its catalog, then execute its tool checks. Use a separate test agent to try new tools without changing an existing production specialist.

Changing only draft tools does not provision the team's catalog. After every named tool-config publication, compare discovered callable tools with the intended config: registry caching can preserve old definitions, including an empty catalog queried before first publication. A server operator can refresh just that specialist with `POST <registry-base>/reload?agent_id=<specialist-id>`, then verify callable tools through `GET <registry-base>/apis?agent_id=<specialist-id>`. Use the configured registry URL; a remote chat client may not have registry administration access. Re-test in a fresh thread.

5. Test the selected supervisor draft through Manage chat or `/stream` with `X-Agent-ID` and `X-Use-Draft: true`. Draft supervisors resolve specialist drafts, falling back to published config when a draft is absent; production uses published specialist configs. Check draft model/instruction/policy changes separately from the published tool catalog. Managed IDs may contain hyphens escaped in delegation function names; use the actual available tool schema instead of constructing names from IDs.
6. Publish validated specialist config changes before publishing the supervisor, using `POST /api/manage/config?agent_id=<id>` and each full authoritative config. Publishing the supervisor neither publishes its specialists nor pins their versions. Re-test the team whenever a referenced specialist is published independently. Preserve credentials as described in `cuga-managed-server`; do not publish redacted GET payloads.

Save this invocation example as `invoke_team.py`. Supply `CUGA_SUPERVISOR_ID` from the creation response, `CUGA_BASE_URL`, and server-required `CUGA_AUTH_TOKEN`. Set `CUGA_USE_DRAFT=true` for a draft test; leave it unset or false for production. `/stream` does not need `/run`'s events feature gate or gateway token. Named supervisors must be selected explicitly; `/run`'s advisory `agent` field is not a substitute.

```python
import os
import uuid

import httpx

headers = {
    "X-Agent-ID": os.environ["CUGA_SUPERVISOR_ID"],
    "X-Thread-ID": "team-check-" + uuid.uuid4().hex,
}
if os.getenv("CUGA_USE_DRAFT", "false").lower() == "true":
    headers["X-Use-Draft"] = "true"
if os.getenv("CUGA_AUTH_TOKEN"):
    headers["Authorization"] = "Bearer " + os.environ["CUGA_AUTH_TOKEN"]
query = os.getenv(
    "CUGA_TEAM_QUERY",
    "Get our top customer from CRM, then pass the returned contact and customer record to the email agent to send a thank-you",
)
with httpx.Client(base_url=os.environ["CUGA_BASE_URL"], timeout=120) as client:
    registry = client.get("/api/ui/config", headers=headers)
    registry.raise_for_status()
    if registry.json().get("agent_registry") is not True:
        raise RuntimeError("Named-agent registry is disabled; refusing default-agent fallback")
    listed = client.get("/api/agents", headers=headers)
    listed.raise_for_status()
    if headers["X-Agent-ID"] not in {agent["id"] for agent in listed.json()["agents"]}:
        raise ValueError("Selected supervisor ID is not registered")
    response = client.post("/stream", headers=headers, json={"query": query})
    response.raise_for_status()
    print(response.text)  # SSE: inspect errors, delegation events and the final answer.
```

Use fixture email delivery or an explicitly authorized test recipient for validation. HTTP 200 or an answer alone does not prove delegation succeeded: inspect tool/delegation errors and the services' recorded arguments. Check both specialists executed, the CRM contact reached email delivery, draft edits left production unchanged, and published changes appeared in a fresh production thread. Record the IDs and published versions. If model/service access is unavailable, report the unverified path.

## Demo entry points

Use `cuga-install-and-launch` for installation and process management. Verify the installed CLI supports the requested preset/flag with `uv run cuga start --help`.

| Command | Purpose |
|---|---|
| `uv run --env-file .env cuga start demo_supervisor` | Preconfigured supervisor demo backed by packaged YAML; verify the runtime-default supervisor model and any specialist model overrides, plus actual tool execution |
| `uv run --env-file .env cuga start manager --seed-supervisor-demo` | Seed CRM, email and filesystem specialists plus `team-supervisor` in the managed registry, including draft and published configs |

Run either demo in a disposable workspace **and with isolated storage**, not merely from a new working directory. The launcher can reset the local config database under the default preservation setting, and package-default storage may be shared across projects. Before launch, set `DYNACONF_STORAGE__MODE=local`, `CUGA_DBS_DIR` and `DYNACONF_STORAGE__LOCAL_DB_PATH` in the demo's `.env` to absolute paths inside that disposable workspace; set `CUGA_LOGGING_DIR` there too and load it with `--env-file`. Use unused service ports and avoid stopping/replacing an existing server. The seeding command writes fixed agent IDs and publishes them; do not run it against an existing customized team. For `manager --seed-supervisor-demo`, inspect the resulting IDs through `/api/agents` and select `team-supervisor` in Manage. `demo_supervisor` uses the default/global YAML supervisor rather than creating that named managed agent. In either case, test a request requiring more than one specialist. A preset that starts or a dashboard that lists agents is not proof that their tools executed.

This skill's validated scope is internal CUGA specialists. External A2A/ACP teams need their own protocol, authentication and execution checks; do not claim those paths were validated by the internal examples.
