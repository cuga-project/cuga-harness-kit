#!/usr/bin/env python
"""
Agent runner — executes test cases from test_cases.json in parallel and writes
one actual_outputs/<test_id>.json per test case alongside traj/<test_id>/ logs.

TEMPLATE: The EVALUATOR fills in:
- The correct import for the agent/supervisor class (replace PLACEHOLDER_MODULE and PLACEHOLDER_CLASS)
- The prediction dir output path (replace PLACEHOLDER_PREDICTION_DIR)
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load CUGA credentials from migration_to/.env
load_dotenv(Path(__file__).parent.parent / ".env")

# Patch LocalExecutor timeout before cuga imports
try:
    from cuga.backend.cuga_graph.nodes.cuga_lite.executors.local.local_executor import LocalExecutor
    LocalExecutor._timeout = 180
    _orig = LocalExecutor.execute
    async def _patched(self, wrapped_code, context_locals, timeout=30, **kwargs):
        return await _orig(self, wrapped_code, context_locals, timeout=180, **kwargs)
    LocalExecutor.execute = _patched
except Exception as e:
    logger.warning(f"Could not patch LocalExecutor timeout: {e}")

# Patch missing settings attributes
try:
    from cuga.config import settings
    _missing = {
        'enable_todos': False, 'e2b_sandbox': False, 'reflection_enabled': False,
        'cuga_lite_max_steps': 50, 'shortlisting_tool_threshold': 10,
        'force_autonomous_mode': False, 'sub_task_keep_last_n': 5,
        'code_executor_keep_last_n': -1, 'tool_call_timeout': 120,
        'code_planner_enabled': False, 'api_planner_hitl': False,
        'use_vision': False, 'mode': 'api', 'save_reuse_generate_html': False,
        'use_location_resolver': False, 'use_paraphrase': False,
        'path_segment_index': 1, 'wxo_integration': False,
        'use_extension': False, 'force_lite_mode_apps': [],
    }
    for attr, val in _missing.items():
        if not hasattr(settings.advanced_features, attr):
            setattr(settings.advanced_features, attr, val)
    settings.advanced_features.tracker_enabled = True
except Exception as e:
    logger.warning(f"Could not patch settings: {e}")

# {{PLACEHOLDER: replace with the correct import}}
from PLACEHOLDER_MODULE import PLACEHOLDER_CLASS as Agent

from cuga.backend.activity_tracker.tracker import ActivityTracker

PREDICTION_DIR = Path("PLACEHOLDER_PREDICTION_DIR")
OUTPUTS_DIR = PREDICTION_DIR / "actual_outputs"
TRAJ_DIR = PREDICTION_DIR / "traj"
LOGS_DIR = PREDICTION_DIR / "logs"
PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
TRAJ_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


async def run_one(agent: Agent, tc: dict) -> None:
    # One log file per test case, filtered by test_id binding so parallel runs don't interleave.
    log_file = LOGS_DIR / f"{tc['test_id']}.log"
    sink_id = logger.add(
        str(log_file), level="DEBUG",
        format="{time} | {level} | {message}",
        filter=lambda r, tid=tc["test_id"]: r["extra"].get("test_id") == tid,
    )
    tc_logger = logger.bind(test_id=tc["test_id"])

    tracker = ActivityTracker()
    tracker.set_base_dir(str(TRAJ_DIR))
    tracker.start_experiment(task_ids=[tc["test_id"]], experiment_name="cuga_eval")
    tracker.reset(intent=tc["input"], task_id=tc["test_id"])

    tc_logger.info(f"INPUT: {tc['input']}")
    try:
        result = await agent.invoke(tc["input"])
        actual_output = result.answer
        error = None
    except Exception as e:
        actual_output = ""
        error = str(e)
    finally:
        logger.remove(sink_id)

    out = {
        "test_id": tc["test_id"],
        "input": tc["input"],
        "expected_output": tc["expected_output"],
        "actual_output": actual_output,
        "error": error,
        "log_path": str(TRAJ_DIR / tc["test_id"]),
    }
    (OUTPUTS_DIR / f"{tc['test_id']}.json").write_text(json.dumps(out, indent=2))
    tc_logger.info(f"  {tc['test_id']}: {'OK' if error is None else f'ERROR: {error}'}")


async def main():
    test_cases = json.loads((Path(__file__).parent / "test_cases.json").read_text())
    agent = await Agent.create()
    await asyncio.gather(*[run_one(agent, tc) for tc in test_cases])
    logger.info(f"Wrote {len(test_cases)} results -> {OUTPUTS_DIR}")


asyncio.run(main())
