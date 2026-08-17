---
name: cuga-build-agent
description: Use when the user wants to write Python code that creates or invokes a CugaAgent or CugaSupervisor, e.g. "build an agent with cuga", "how do I call agent.invoke", "set up a multi-agent supervisor".
---

# Building with the CugaAgent SDK

## Single agent

```python
from cuga import CugaAgent
from langchain_core.tools import tool
import asyncio

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

agent = CugaAgent(tools=[add_numbers])

async def main():
    result = await agent.invoke("What is 5 + 3?")
    print(result.answer)

asyncio.run(main())
```

Key points:
- Tools are plain LangChain `@tool`-decorated functions (or an OpenAPI/MCP provider — see `cuga-build-tool`).
- `await agent.invoke(message, thread_id=...)` — `thread_id` isolates conversation state per user/session; omit it for a one-off call.
- `agent.stream()` gives real-time execution events instead of a single final result.
- `agent.policies` is the entry point for attaching Intent Guard / Playbook / Tool Approval / Tool Guide / Output Formatter policies programmatically — see `cuga-author-policy`.
- Knowledge/RAG is on by default (`enable_knowledge=True`) — see `cuga-knowledge-rag`; pass `enable_knowledge=False` to turn it off.
- The underlying LangGraph graph is reachable for advanced use cases (custom nodes, inspecting state) if the simple API isn't enough.

## Multi-agent (CugaSupervisor)

```python
from cuga import CugaAgent, CugaSupervisor
from langchain_core.tools import tool
import asyncio

@tool
def get_customers(limit: int = 10) -> str:
    """Fetch top customers from CRM."""
    return "Alice ($250k); Bob ($180k)"

@tool
def send_email(to: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"

async def main():
    crm_agent = CugaAgent(tools=[get_customers])
    crm_agent.description = "CRM and customer data"

    email_agent = CugaAgent(tools=[send_email])
    email_agent.description = "Sending emails and notifications"

    supervisor = CugaSupervisor(agents={"crm": crm_agent, "email": email_agent})
    result = await supervisor.invoke("Get our top customer and email them a thank-you")
    print(result.answer)

asyncio.run(main())
```

- Each sub-agent needs a `.description` — the supervisor uses it to decide who handles what.
- Mix local `CugaAgent`s with remote agents via A2A: pass an `"agent_name": {"type": "external", "description": "...", "config": {"a2a_protocol": {...}}}` entry in `agents=`.
- Pass data between sub-agents with `variables=["var_name"]`.
- `CugaSupervisor.from_yaml("path/to/config.yaml")` loads agents from a config file instead of constructing them in code.
- Try it live first: `uv run cuga start demo_supervisor` (see `cuga-install-and-launch`).

## Reference

Full SDK docs: https://docs.cuga.dev/docs/sdk/cuga_agent/ and https://docs.cuga.dev/docs/sdk/cuga_supervisor
