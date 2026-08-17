"""
{{PLACEHOLDER: replace "MyAgent" with the agent class name from the spec}}
{{PLACEHOLDER: update docstring to describe what this agent does}}

Single CugaAgent with all MCP tools and skill-based task routing.
Each skill is a self-contained end-to-end workflow.

Skills are discovered from .agents/skills/ and exposed via the load_skill() tool.

Usage:
    from my_agent import MyAgent  # {{PLACEHOLDER: update import name}}

    agent = await MyAgent.create()
    result = await agent.invoke("Your task here")
    print(result.answer)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

# Use the `.agents/skills/` universal layout (matches where skill_template/SKILL.md
# is placed below) instead of CUGA's native default (`.cuga/skills/`). This MUST be
# set before the first `cuga` import: dynaconf resolves DYNACONF_* env vars when the
# Settings object is constructed (on import of cuga.config), not on each access —
# setting it later (e.g. inside create()) is silently ignored.
os.environ.setdefault("DYNACONF_SKILLS__ROOT", "agents")

from cuga import CugaAgent
from cuga.config import settings

try:
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
except ImportError:
    try:
        from langfuse.callback.langchain import LangchainCallbackHandler as LangfuseCallbackHandler
    except ImportError:
        logger.warning("Langfuse is not installed, tracing will be disabled")
        LangfuseCallbackHandler = None

_HERE = Path(__file__).parent
_CONFIG = _HERE / "agent_config.yaml"
_CUGA_FOLDER = str(_HERE / ".cuga")


async def _load_mcp_tools(
    server_names: List[str],
    url_registry: Dict[str, str],
) -> List[Any]:
    if not server_names:
        return []

    from langchain_mcp_adapters.client import MultiServerMCPClient

    connections: Dict[str, Any] = {}
    for name in server_names:
        url = url_registry.get(name)
        if not url:
            logger.warning(f"MCP server '{name}' not in registry — skipping")
            continue
        connections[name] = {"url": url, "transport": "sse"}

    if not connections:
        return []

    try:
        tools = await MultiServerMCPClient(connections).get_tools()
        logger.info(f"Loaded {len(tools)} tool(s) from {list(connections)}")
        return tools
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}")
        return []


class MyAgent:  # {{PLACEHOLDER: rename to match the spec's entrypoint_module}}

    def __init__(self, agent: CugaAgent):
        self._agent = agent

    @classmethod
    async def create(cls) -> "MyAgent":  # {{PLACEHOLDER: update return type annotation}}
        os.environ["CUGA_FOLDER"] = _CUGA_FOLDER

        with open(_CONFIG) as f:
            config = yaml.safe_load(f)

        langfuse_handler: Optional[Any] = None
        if settings.advanced_features.langfuse_tracing and LangfuseCallbackHandler is not None:
            try:
                langfuse_handler = LangfuseCallbackHandler()
                logger.info("Langfuse tracing enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse handler: {e}")

        url_registry: Dict[str, str] = {
            srv["name"]: srv["url"]
            for srv in config.get("mcp_servers", [])
            if srv.get("name") and srv.get("url")
        }

        all_tools = await _load_mcp_tools(
            server_names=list(url_registry.keys()),
            url_registry=url_registry,
        )

        callbacks = [langfuse_handler] if langfuse_handler else None

        # enable_knowledge=True: activates CUGA's native knowledge engine.
        # Any source knowledge base / RAG functionality is covered here — no custom MCP server needed.
        # enable_skills=True: activates skills discovery (load_skill tool + prompt block).
        # Skills are OFF by default (settings.skills.enabled=false in settings.toml) — this
        # constructor override is required or .agents/skills/*/SKILL.md is silently ignored.
        agent = CugaAgent(
            tools=all_tools,
            tool_provider=None,
            cuga_folder=_CUGA_FOLDER,
            callbacks=callbacks,
            enable_knowledge=True,
            enable_skills=True,
            reset_policy_storage=True,
            auto_load_policies=False,
            filesystem_sync=False,
        )

        await agent.policies.load_from_folder(_CUGA_FOLDER)
        return cls(agent)

    async def invoke(self, message: str, thread_id: str | None = None, **kwargs):
        return await self._agent.invoke(message, thread_id=thread_id, **kwargs)

    async def stream(self, message: str, thread_id: str | None = None, **kwargs):
        async for chunk in self._agent.stream(message, thread_id=thread_id, **kwargs):
            yield chunk


if __name__ == "__main__":
    import asyncio

    async def main():
        agent = await MyAgent.create()
        result = await agent.invoke("Hello")  # {{PLACEHOLDER: replace with a real example query}}
        print(result.answer)

    asyncio.run(main())
