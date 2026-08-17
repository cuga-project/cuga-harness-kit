"""
{{PLACEHOLDER: replace "MySupervisor" with the supervisor class name from the spec}}
{{PLACEHOLDER: replace the module docstring with what this supervisor does}}

CugaSupervisor orchestrating external A2A-wrapped agents.

Goal: CugaSupervisor acts as the orchestration layer, routing tasks to external
agents that run as independent HTTP services and are exposed via the A2A protocol.
The supervisor itself has no tools — the CugaSupervisor LLM reads agent descriptions
from supervisor_config.yaml to decide which external agent(s) to call.

Usage:
    from my_supervisor import MySupervisor  # {{PLACEHOLDER: update import name}}

    supervisor = await MySupervisor.create()
    result = await supervisor.invoke("Your task here")
    print(result.answer)
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger

from cuga import CugaSupervisor

_HERE = Path(__file__).parent
_CONFIG = _HERE / "supervisor_config.yaml"
_CUGA_FOLDER = str(_HERE / ".cuga")

# CUGA_FOLDER (plain env var) is read by the CugaLite/skills runtime paths, but NOT by
# CugaSupervisor's own policy engine — that only reads the `cuga_folder=` constructor
# kwarg passed below (or falls back to the relative `settings.policy.cuga_folder`
# default, which breaks if the process CWD != this directory). Set both so policy
# loading (.cuga/intent_guards, playbooks, output_formatters, tool_guides) works
# regardless of where this script is launched from.
os.environ.setdefault("CUGA_FOLDER", _CUGA_FOLDER)


class MySupervisor:  # {{PLACEHOLDER: rename to match the spec's supervisor class name}}

    def __init__(self, supervisor: CugaSupervisor):
        self._supervisor = supervisor

    @classmethod
    async def create(cls) -> "MySupervisor":  # {{PLACEHOLDER: update return type annotation}}
        with open(_CONFIG) as f:
            config = yaml.safe_load(f)

        agents: Dict[str, Any] = {}
        for agent_cfg in config.get("agents", []):
            name = agent_cfg["name"]
            a2a = agent_cfg.get("a2a_protocol", {})
            if a2a.get("enabled"):
                # Register as an external agent — NOT a CugaAgent instance.
                # CugaSupervisor will reach it at runtime via HTTP using the A2A protocol.
                # The "description" field is what the supervisor LLM uses for routing.
                agents[name] = {"type": "external", "config": agent_cfg}
                logger.info(f"Registered external A2A agent: {name} -> {a2a.get('endpoint')}")
            else:
                logger.warning(f"Skipping agent without a2a_protocol.enabled: {name}")

        supervisor_cfg = config.get("supervisor", {})
        # cuga_folder= (absolute path) makes policy auto-loading (auto_load_policies
        # defaults to True via settings.policy.auto_load_policies) find .cuga/ regardless
        # of the process's current working directory. There are no internal CugaAgent
        # sub-agents in this template to attach policies to (all agents are external A2A
        # services) — policies here apply to the supervisor itself.
        supervisor = CugaSupervisor(
            agents=agents,
            special_instructions=supervisor_cfg.get("special_instructions"),
            cuga_folder=_CUGA_FOLDER,
        )
        return cls(supervisor)

    async def invoke(self, message: str, thread_id: str | None = None, **kwargs):
        return await self._supervisor.invoke(message, thread_id=thread_id, **kwargs)

    # CugaSupervisor does not implement stream() — use invoke() for all supervisor calls.


if __name__ == "__main__":
    import asyncio

    async def main():
        supervisor = await MySupervisor.create()
        result = await supervisor.invoke(
            "{{PLACEHOLDER: replace with a real example query}}"
        )
        print(result.answer)

    asyncio.run(main())
