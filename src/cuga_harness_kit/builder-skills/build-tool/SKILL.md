---
name: cuga-build-tool
description: Use when the user wants to give a cuga agent a new capability via a Python function, REST/OpenAPI service, or MCP server, e.g. "add a tool", "connect this API to cuga", "register an MCP server".
---

# Registering tools with cuga

cuga supports three tool integration types:

| Type | Best for | Configured via | Loading |
|---|---|---|---|
| **LangChain** | Python functions, rapid prototyping | direct import, pass to `CugaAgent(tools=[...])` | Runtime |
| **OpenAPI** | REST APIs, existing services | Registry YAML or managed `config.tools` | Registry startup/reload |
| **MCP** | Custom protocols, complex integrations | Registry YAML or managed `config.tools` | Registry startup/reload |

## LangChain tool (fastest path)

```python
from langchain_core.tools import tool

@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by ID and return its status."""
    return f"Order {order_id}: shipped"

from cuga import CugaAgent

agent = CugaAgent(tools=[lookup_order], enable_knowledge=False)
```

This is a runtime-loaded tool: no config file, no restart needed, just pass it into the `CugaAgent` constructor. Write a clear docstring — it becomes the tool description the agent's reasoning engine sees.

## OpenAPI / MCP (registry-based)

For a standalone registry, write a project-local `mcp_servers.yaml` and point `MCP_SERVERS_FILE` at its absolute path before launching `uv run cuga start registry`. Do not modify files inside the installed package. These are registry configuration, not Python build-time dependencies; restart/reload after edits.

```yaml
services:
  - orders:
      url: http://localhost:9000/openapi.json
      description: Order service
      include: [lookupOrder]
mcpServers:
  orders_mcp:
    url: http://localhost:9001/mcp
    transport: http
    description: Order lookup tools
```

In manager mode, configure tools through Manage or the draft API, test, then publish (`cuga-managed-server`). Its generated `managed_mcp_servers.yaml` is derived from saved config. Python SDK tools are in-process; to make the same function available to the managed server expose it over MCP/OpenAPI.

The SDK can also load MCP tools directly with `langchain_mcp_adapters.client.MultiServerMCPClient` and pass the resulting tools to `CugaAgent(tools=...)`; install the adapter dependency explicitly. A standalone registry does not automatically attach itself to an SDK agent.

See the registry's own README for the exact config schema and worked examples: `src/cuga/backend/tools_env/registry/README.md`, plus `docs/examples/cuga_with_runtime_tools/README.md` for a full walkthrough combining different tool types with MCP.

## Which to reach for

- One-off Python function, prototyping, or logic that lives in your app already → LangChain tool.
- An existing REST API you don't want to hand-wrap → OpenAPI entry in `mcp_servers.yaml`.
- A third-party or custom MCP server → MCP entry in `mcp_servers.yaml`.

## Enhancing how the agent uses a tool

Once a tool exists, you can shape *how* the agent uses it without touching its code — that's a `tool_guide` or `tool_approval` policy (require confirmation before a sensitive tool runs, or append extra usage guidance/examples to its description). See `cuga-author-policy`.
