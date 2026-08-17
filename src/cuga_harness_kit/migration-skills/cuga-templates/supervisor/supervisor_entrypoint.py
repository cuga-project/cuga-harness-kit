"""
{{PLACEHOLDER: replace "MySupervisor" with the supervisor class name from the spec}}
{{PLACEHOLDER: replace the module docstring with a description of what this supervisor does}}

Supervisor entrypoint.

Task decomposition and agent routing are handled natively by the CugaSupervisor
LLM, guided by enriched agent descriptions in supervisor_config.yaml and
playbooks/policies in .cuga/.

Usage:
    from my_supervisor import MySupervisor  # {{PLACEHOLDER: update import name}}

    supervisor = await MySupervisor.create()
    result = await supervisor.invoke("Your task here")
    print(result.answer)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from cuga import CugaAgent, CugaSupervisor
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
_CONFIG = _HERE / "supervisor_config.yaml"


async def _load_mcp_tools(
    server_names: List[Any],
    url_registry: Dict[str, str],
    agent_name: str,
) -> List[Any]:
    if not server_names:
        return []

    from langchain_mcp_adapters.client import MultiServerMCPClient

    connections: Dict[str, Any] = {}
    for entry in server_names:
        name = entry if isinstance(entry, str) else entry.get("name", "")
        url = url_registry.get(name)
        if not url:
            logger.warning(f"[{agent_name}] MCP server '{name}' not in registry — skipping")
            continue
        connections[name] = {"url": url, "transport": "sse"}

    if not connections:
        return []

    try:
        tools = await MultiServerMCPClient(connections).get_tools()
        logger.info(f"[{agent_name}] Loaded {len(tools)} tool(s) from {list(connections)}")
        return tools
    except Exception as e:
        logger.error(f"[{agent_name}] Failed to load MCP tools: {e}")
        return []


class MySupervisor:  # {{PLACEHOLDER: rename to match the spec's entrypoint_module}}

    def __init__(self, supervisor: CugaSupervisor):
        self._supervisor = supervisor

    @classmethod
    async def create(cls) -> "MySupervisor":  # {{PLACEHOLDER: update return type annotation}}
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

        agents: Dict[str, Any] = {}
        callbacks = [langfuse_handler] if langfuse_handler else None

        for agent_cfg in config.get("agents", []):
            name = agent_cfg["name"]
            if "a2a_protocol" in agent_cfg and agent_cfg.get("a2a_protocol", {}).get("enabled"):
                agents[name] = {"type": "external", "config": agent_cfg}
                continue

            tools = await _load_mcp_tools(
                server_names=agent_cfg.get("mcp_servers", []),
                url_registry=url_registry,
                agent_name=name,
            )
            # enable_knowledge: set to True in supervisor_config.yaml for agents that
            # need knowledge base / RAG access — CUGA's native knowledge engine handles
            # retrieval without a custom MCP server.
            enable_knowledge = agent_cfg.get("enable_knowledge", False)
            agent = CugaAgent(
                tools=tools,
                tool_provider=None,
                special_instructions=agent_cfg.get("special_instructions"),
                callbacks=callbacks,
                enable_knowledge=enable_knowledge if enable_knowledge else None,
            )
            # CugaAgent.__init__ does not accept `description`; the supervisor reads it
            # via getattr (see prepare_agents_and_prompt.py). Only set when YAML provides
            # one — an empty string would defeat the supervisor's "Internal agent: <name>"
            # fallback.
            if agent_cfg.get("description"):
                agent.description = agent_cfg["description"]
            agents[name] = agent

        supervisor_special_instructions = config.get("supervisor", {}).get("special_instructions")
        supervisor = CugaSupervisor(
            agents=agents,
            callbacks=callbacks,
            special_instructions=supervisor_special_instructions,
        )

        policies_folder = str(_HERE / ".cuga")
        for agent in supervisor._agents.values():
            if hasattr(agent, "policies"):
                await agent.policies.load_from_folder(policies_folder)

        return cls(supervisor)

    async def invoke(self, message: str, thread_id: str | None = None, **kwargs):
        return await self._supervisor.invoke(message, thread_id=thread_id, **kwargs)

    # CugaSupervisor does not implement stream() — use invoke() for all supervisor calls.


if __name__ == "__main__":
    import asyncio

    async def main():
        supervisor = await MySupervisor.create()
        result = await supervisor.invoke("Hello")  # {{PLACEHOLDER: replace with a real example query}}
        print(result.answer)

    asyncio.run(main())
