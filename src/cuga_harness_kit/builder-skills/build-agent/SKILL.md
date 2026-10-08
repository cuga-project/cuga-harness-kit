---
name: cuga-build-agent
description: Use when writing Python code that creates or invokes a single CugaAgent, embeds CUGA in an app, or uses agent.invoke/stream. Multi-agent composition uses cuga-build-supervisor.
---

# Building with the CugaAgent SDK

This path embeds CUGA in your Python process, usually as the backend of your own application/UI or an existing Python service. It does not provide a custom UI automatically or publish configuration to `cuga start manager`; for managed configuration use `cuga-managed-server`. For a new build, use `using-cuga` to verify the chosen LLM and establish the user's goal/mode first. Reuse that result when already completed. A model is required for agent reasoning even when tools are local.

## Single agent

```python
from cuga import CugaAgent
from langchain_core.tools import tool
import asyncio

@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

async def main():
    agent = CugaAgent(tools=[add_numbers], enable_knowledge=False)
    try:
        result = await agent.invoke("What is 5 + 3?", track_tool_calls=True)
        if result.error:
            raise RuntimeError(result.error)
        print(result.answer)
        print(result.tool_calls)  # verify add_numbers actually ran
    finally:
        await agent.aclose()

asyncio.run(main())
```

Key points:
- Tools are plain LangChain `@tool`-decorated functions (or an OpenAPI/MCP provider — see `cuga-build-tool`).
- `await agent.invoke(message, thread_id=...)` — `thread_id` isolates conversation state per user/session; omit it for a one-off call.
- `agent.stream()` gives real-time execution events instead of a single final result.
- `agent.policies` is the entry point for attaching Intent Guard / Playbook / Tool Approval / Tool Guide / Output Formatter policies programmatically — see `cuga-author-policy`.
- `enable_knowledge=None` follows the installed settings; use `True` or `False` explicitly when needed. For Knowledge/RAG see `cuga-knowledge-rag`; pass `enable_knowledge=False` to turn it off.
- The underlying LangGraph graph is reachable for advanced use cases (custom nodes, inspecting state) if the simple API isn't enough.

## Multi-agent

Use `cuga-build-supervisor` for SDK specialist agents, delegation, cleanup and managed-team equivalents. Preserve the SDK/server choice established by `using-cuga`.

## Reference

Full SDK docs: https://docs.cuga.dev/docs/sdk/cuga_agent/ and https://docs.cuga.dev/docs/sdk/cuga_supervisor
