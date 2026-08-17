---
name: cuga-build-tool
description: Use when the user wants to give a cuga agent a new capability via a Python function, REST/OpenAPI service, or MCP server, e.g. "add a tool", "connect this API to cuga", "register an MCP server".
---

# Registering tools with cuga

cuga supports three tool integration types:

| Type | Best for | Configured via | Loading |
|---|---|---|---|
| **LangChain** | Python functions, rapid prototyping | direct import, pass to `CugaAgent(tools=[...])` | Runtime |
| **OpenAPI** | REST APIs, existing services | `mcp_servers.yaml` | Build-time |
| **MCP** | Custom protocols, complex integrations | `mcp_servers.yaml` | Build-time |

## LangChain tool (fastest path)

```python
from langchain_core.tools import tool

@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by ID and return its status."""
    ...

agent = CugaAgent(tools=[lookup_order])
```

This is a runtime-loaded tool: no config file, no restart needed, just pass it into the `CugaAgent` constructor. Write a clear docstring — it becomes the tool description the agent's reasoning engine sees.

## OpenAPI / MCP (registry-based)

For REST APIs or MCP servers, add an entry to `mcp_servers.yaml` (path: `src/cuga/backend/tools_env/registry/config/mcp_servers.yaml` in a cuga-agent checkout). These are build-time: the tool registry (`cuga start registry`, or bundled into any `demo_*`/`manager` service) loads this config at startup, so changes need a restart to take effect.

See the registry's own README for the exact config schema and worked examples: `src/cuga/backend/tools_env/registry/README.md`, plus `docs/examples/cuga_with_runtime_tools/README.md` for a full walkthrough combining different tool types with MCP.

## Which to reach for

- One-off Python function, prototyping, or logic that lives in your app already → LangChain tool.
- An existing REST API you don't want to hand-wrap → OpenAPI entry in `mcp_servers.yaml`.
- A third-party or custom MCP server → MCP entry in `mcp_servers.yaml`.

## Enhancing how the agent uses a tool

Once a tool exists, you can shape *how* the agent uses it without touching its code — that's a `tool_guide` or `tool_approval` policy (require confirmation before a sensitive tool runs, or append extra usage guidance/examples to its description). See `cuga-author-policy`.
