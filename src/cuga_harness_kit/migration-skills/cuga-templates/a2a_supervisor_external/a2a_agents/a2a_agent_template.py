"""
{{PLACEHOLDER: replace "MyAgent" with the agent name, e.g. "CalculatorAgent", "SearchAgent"}}
{{PLACEHOLDER: replace the module docstring with what this agent does}}

<Agent Name> — {{PLACEHOLDER: one-line description of what it does}}, served via A2A.

Tools: {{PLACEHOLDER: list the tools this agent exposes, e.g. "tool_one, tool_two"}}
Port:  {{PLACEHOLDER: default port, e.g. 8001}} (override with {{PLACEHOLDER: MY_AGENT_PORT}} env var)

Run: uv run python a2a_agents/my_agent.py  # {{PLACEHOLDER: update filename}}

VERIFIED against a2a-sdk==1.0.2 (the version pinned in migration_to/cuga-agent/uv.lock).
This version replaced the old monolithic `A2AStarletteApplication` with two
route-builder functions (`create_jsonrpc_routes`, `create_agent_card_routes`) that
you mount on a plain `starlette.applications.Starlette`. `AgentCard` is now a
protobuf message (no `url=` field — the endpoint lives in `supported_interfaces`),
and the old `a2a.utils.message.new_agent_text_message` helper moved to
`a2a.helpers.new_text_message`. CUGA's own A2A client
(cuga/backend/cuga_graph/nodes/cuga_supervisor/a2a_protocol.py) always speaks the
v0.3 JSON-RPC wire shape and expects the answer text at
`result.status.message.parts[].text` on a `kind: "task"` envelope — so
`enable_v0_3_compat=True` on `create_jsonrpc_routes` is required, and the executor
must enqueue a `Task` before any `TaskStatusUpdateEvent` (see `_run_and_respond`
below). This exact pattern was round-tripped against a real a2a-sdk 1.0.2 Starlette
TestClient — request in, `result.status.message.parts[0].text` out — during the
2026-07-27 template sync.
"""

import os

import uvicorn
from starlette.applications import Starlette

from a2a.helpers import new_task_from_user_message, new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

PORT = int(os.getenv("MY_AGENT_PORT", "8001"))   # {{PLACEHOLDER: update env var and default port}}
HOST = os.getenv("MY_AGENT_HOST", "0.0.0.0")     # {{PLACEHOLDER: update env var name}}
RPC_PATH = "/a2a"


# ── Agent tools ────────────────────────────────────────────────────────────────
#
# {{PLACEHOLDER: import or define the tools / logic this agent will use.
#   Options:
#   A) LangChain @tool functions — use create_react_agent from langgraph.prebuilt
#   B) Plain Python functions — call them directly in _run()
#   C) Any other framework — wrap its output as a string in _run()
# }}
#
# Example (LangChain tools):
#
# from langchain_core.tools import tool
#
# @tool
# def my_tool(input: str) -> str:
#     """{{PLACEHOLDER: describe what this tool does.}}"""
#     return f"processed: {input}"
#
# _TOOLS = [my_tool]  # {{PLACEHOLDER: add all tools to this list}}


# ── LLM ────────────────────────────────────────────────────────────────────────
#
# {{PLACEHOLDER: configure the LLM for this agent.
#   Copy the pattern below and add/remove provider blocks as needed.}}
#
# def _build_llm():
#     model_override = os.getenv("MY_AGENT_MODEL")
#     if os.getenv("WATSONX_API_KEY"):
#         from langchain_ibm import ChatWatsonx
#         model = model_override or os.getenv("MODEL_NAME", "openai/gpt-oss-120b")
#         return ChatWatsonx(
#             model_id=model,
#             url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
#             project_id=os.getenv("WATSONX_PROJECT_ID") or None,
#             space_id=os.getenv("WATSONX_SPACE_ID") or None,
#         )
#     if os.getenv("OPENAI_API_KEY"):
#         from langchain_openai import ChatOpenAI
#         model = model_override or "gpt-4o-mini"
#         return ChatOpenAI(model=model, temperature=0)
#     raise RuntimeError("Set WATSONX_API_KEY or OPENAI_API_KEY in .env")


# ── Agent graph / runner ────────────────────────────────────────────────────────
#
# {{PLACEHOLDER: build your agent graph or runner here.
#   Example (LangGraph ReAct):
#
#   from langgraph.prebuilt import create_react_agent
#
#   _graph = None
#
#   def _get_graph():
#       global _graph
#       if _graph is None:
#           _graph = create_react_agent(_build_llm(), tools=_TOOLS)
#       return _graph
# }}


async def _run(task: str) -> str:
    """Execute the task and return a string result.

    {{PLACEHOLDER: implement the agent's core logic here.
      - Invoke your LangGraph graph, LLM, or custom logic.
      - Return a plain string — this is wrapped into the A2A Task's status message.
      Example (LangGraph ReAct):
        graph = _get_graph()
        result = await graph.ainvoke({"messages": [{"role": "user", "content": task}]})
        return result["messages"][-1].content
    }}
    """
    raise NotImplementedError("{{PLACEHOLDER: implement _run()}}")


# ── A2A executor ────────────────────────────────────────────────────────────────
#
# CUGA's client (delegate_task_via_a2a_sdk) reads the answer from
# result.status.message.parts[].text on a completed Task — never from a bare
# Message event. That means every execute() call must:
#   1. Enqueue a Task first (new_task_from_user_message) — the SDK raises
#      "Agent should enqueue Task before TaskStatusUpdateEvent event" otherwise.
#   2. Enqueue a terminal TaskStatusUpdateEvent (via TaskUpdater.update_status)
#      carrying the answer as its `message`.


class MyAgentExecutor(AgentExecutor):  # {{PLACEHOLDER: rename to match agent name, e.g. CalculatorAgentExecutor}}
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_text = context.get_user_input()

        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            result = await _run(task_text)
        except Exception as exc:
            logger.error(f"{{PLACEHOLDER: AgentName}} execution error: {exc}")
            await updater.update_status(
                TaskState.TASK_STATE_FAILED,
                message=new_text_message(
                    f"Error: {exc}",  # {{PLACEHOLDER: customize error message}}
                    context_id=task.context_id,
                    task_id=task.id,
                ),
            )
            return

        await updater.update_status(
            TaskState.TASK_STATE_COMPLETED,
            message=new_text_message(result, context_id=task.context_id, task_id=task.id),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel not supported")


# ── A2A server ──────────────────────────────────────────────────────────────────


def build_app() -> Starlette:
    executor = MyAgentExecutor()  # {{PLACEHOLDER: update to your executor class name}}
    task_store = InMemoryTaskStore()

    agent_card = AgentCard(
        name="MyAgent",  # {{PLACEHOLDER: replace with the agent's display name}}
        description=(
            "{{PLACEHOLDER: Write a full description of what this agent can do. "
            "This is exposed via the A2A /.well-known/agent-card.json endpoint and "
            "should cover: capabilities, input format, output format.}}"
        ),
        version="1.0.0",
        # supported_interfaces replaces the old top-level `url=` field — AgentCard
        # is a protobuf message in a2a-sdk 1.0.2, not a pydantic model.
        supported_interfaces=[
            AgentInterface(
                url=f"http://localhost:{PORT}{RPC_PATH}",
                protocol_binding="JSONRPC",
                protocol_version="0.3",
            )
        ],
        capabilities=AgentCapabilities(),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            # {{PLACEHOLDER: add one AgentSkill per logical capability this agent exposes}}
            AgentSkill(
                id="skill_one",  # {{PLACEHOLDER: snake_case skill id}}
                name="Skill One",  # {{PLACEHOLDER: human-readable skill name}}
                description="{{PLACEHOLDER: what this skill does}}",
                tags=["{{PLACEHOLDER: tag1}}", "{{PLACEHOLDER: tag2}}"],
            ),
            # {{PLACEHOLDER: copy the block above for each additional skill}}
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    # enable_v0_3_compat=True is required: CUGA's supervisor always sends the
    # v0.3 JSON-RPC method name ("message/send") and parses v0.3-shaped Task
    # envelopes. Without it, requests fail with "Method not found".
    routes = create_jsonrpc_routes(
        request_handler,
        rpc_url=RPC_PATH,
        enable_v0_3_compat=True,
    ) + create_agent_card_routes(agent_card)

    return Starlette(routes=routes)


if __name__ == "__main__":
    app = build_app()
    logger.info(f"Starting {{PLACEHOLDER: AgentName}} A2A server at http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
