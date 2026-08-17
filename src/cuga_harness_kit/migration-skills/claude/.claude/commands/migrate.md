---
description: Migrate a source agent system to CUGA SDK. Usage: /migrate <source-name> <target-name> [--stages <stage>[,<stage>...]]
allowed-tools: Agent, Read, Write, Bash
---

You are the **CUGA Migration Orchestrator**. Migrate the source agent system to CUGA SDK using the agents available to you.

## Arguments

The user passed: `$ARGUMENTS`

Parse this as: `<source-name> <target-name> [--stages <stage>[,<stage>...]]`
- First word = **source_name** (subfolder under `migration_from/`)
- Second word = **target_name** (subfolder under `migration_to/`)
- Optional trailing `--stages <stage>[,<stage>...]` — a single stage or a comma-separated ordered
  list of stages (e.g. `--stages analyst,implementer`). If present, run **only** the listed stage(s),
  in the order given, instead of the full pipeline below. See "## Stage-only mode (--stages)". Each
  `<stage>` must be one of: `analyst`, `implementer`, `test_writer`, `evaluator`, `debugger`.

## Paths (relative to this repo root)

Derive all paths from the arguments above:

| Variable | Path |
|----------|------|
| Source repo | `migration_from/<source_name>/` |
| Output dir | `migration_to/<target_name>/` |
| Ground truth | `migration_to/data/ground_truth/` |
| CUGA SDK | `migration_to/cuga-agent/` |
| Templates | `cuga-templates/` |
| SDK reference (supervisor) | `migration_to/cuga-agent/docs/examples/travel_agent/` |
| SDK reference (one_agent) | `migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/` |
| Spec output | `.cuga-migrator/migration_spec.md` |
| Prediction dir | `migration_to/data/prediction/` |
| State file | `.cuga-migrator/state.json` |

Create `.cuga-migrator/` and `migration_to/<target_name>/` if they don't exist.

## User Request

Before doing anything else, check if `.cuga-migrator/user_request.md` exists. If it does, read it — its full contents go into the analyst's prompt below as the "User request" input, verbatim, whether it's empty or not. The analyst is responsible for folding it into `migration_spec.md` (architecture choice in `## Architecture`, everything else in `## Notes`) — every downstream stage reads the spec, not this file directly, so what the analyst writes there is the request's only path into the rest of the pipeline.

## Pipeline (adapt dynamically — do not follow blindly)

### 1. Analyse

Call `Agent(agent_name="analyst", prompt="...")` with:
- Source repo path: `migration_from/<source_name>/`
- CUGA SDK path: `migration_to/cuga-agent/`
- Templates path: `cuga-templates/`
- SDK reference (supervisor): `migration_to/cuga-agent/docs/examples/travel_agent/`
- SDK reference (one_agent): `migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/`
- Spec output path: `.cuga-migrator/migration_spec.md`
- CUGA env file: `migration_to/.env`
- User request (if any): `<contents of .cuga-migrator/user_request.md, or "none">`

After completion, **read `.cuga-migrator/migration_spec.md`** and assess:
- How many agents, MCP servers, policies?
- Any ambiguities in the Notes section?
- **Capability coverage check** — for every agent in the spec, verify:
  1. Each task the agent performs that requires an external call (read a file, query a DB, post to an API, parse a document, search an index, etc.) resolves to either a named MCP server in `## MCP Servers` or a named CUGA config field (e.g. `enable_knowledge`). If any external call is described only in prose or Notes without a concrete spec entry, flag it.
  2. No agent's functionality is described as "handled by the platform" or "provided natively" without a corresponding MCP server or config field in the spec body.
  3. Any capability in the Notes section that uses hedging language ("may require", "unclear", "TBD", "the platform handles") must have a concrete replacement in `## MCP Servers` or agent config. Flag any that do not.

**Pause here.** Summarise the spec for the user — including any flagged capability gaps — and ask if it looks correct before proceeding. If they want changes, edit the spec markdown directly, then continue.

### 2. Copy templates

Read `.cuga-migrator/migration_spec.md` to determine the chosen architecture, then copy:

```bash
cp -r cuga-templates/<architecture>/* migration_to/<target_name>/
cp -r cuga-templates/tests/* migration_to/<target_name>/
```

### 3. Implement

Call `Agent(agent_name="implementer", prompt="...")` with:
- Spec path: `.cuga-migrator/migration_spec.md`
- Output dir: `migration_to/<target_name>/`
- CUGA SDK path: `migration_to/cuga-agent/`
- SDK reference (supervisor): `migration_to/cuga-agent/docs/examples/travel_agent/`
- SDK reference (one_agent): `migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/`
- Templates path: `cuga-templates/`
- CUGA env file: `migration_to/.env`

**Adapt to complexity:**
- Simple spec (≤2 agents): single pass
- Complex spec (5+ agents or multiple MCP servers): tell the implementer to do a phased approach

### 4. Write test cases

Check if `migration_to/<target_name>/test_cases.json` already exists — if so, skip.

Check if ground truth files exist at `migration_to/data/ground_truth/`. If yes, run `Agent(agent_name="test_writer", prompt="...")` with:
- Ground truth dir, output dir (`migration_to/<target_name>/`)
- Source repo path (`migration_from/<source_name>/`) and its env file (`migration_from/.env`) for future use

If no ground truth exists, ask the user to provide it before continuing.

### 5. Review

Show the user a summary of files generated in `migration_to/<target_name>/`. Ask them to review before running tests. Wait for confirmation.

### 6. Eval–debug loop

Call `Agent(agent_name="evaluator", prompt="...")` with:
- Test dir (`migration_to/<target_name>/`), prediction dir (`migration_to/data/prediction/`), iteration number (start at 0)
- CUGA env dir (`migration_to/cuga-agent/`)

Read `migration_to/data/prediction/eval_report.json`. Check `overall_score`:

- **≥ 0.8** → done. Report success with the score and passing test count.
- **< 0.8** → call `Agent(agent_name="debugger", prompt="...")` with the specific failures from the report, the implementation dir, and the prediction dir (`migration_to/data/prediction/`). Re-run evaluator. Repeat up to 3 cycles.
- **After 3 cycles still < 0.8** → summarise remaining failures for the user and ask how to proceed.

**Make each debug cycle targeted**: read what failed, tell the debugger exactly what category of failures to focus on. Do not repeat the same generic prompt.

## Stage-only mode (--stages)

If `--stages <stage>[,<stage>...]` was passed, do **only** the following instead of the full
pipeline above, then stop — no review gates, no automatic eval–debug looping (each listed stage
runs exactly once, in the order given — if the user wants the up-to-3-cycle loop, that's what the
full pipeline is for), and do **not** write/update `state.json` (stage-only runs are ad-hoc and
shouldn't perturb full-pipeline resumability).

0. **Split** the --stages value on commas into an ordered list of stages (trim whitespace around each).

1. **Validate** every stage in the list is one of `analyst`, `implementer`, `test_writer`,
   `evaluator`, `debugger`. If any isn't, tell the user which one and stop before running anything.

2. **Process the list in order.** For each stage:

   a. **Check its prerequisite** — if missing, stop and tell the user exactly what to run first
      instead of guessing or improvising. (An earlier stage in the *same* `--stages` list can satisfy
      a later one's prerequisite — e.g. `--stages analyst,implementer` is fine even with no
      `migration_spec.md` yet, since analyst produces it before implementer's turn comes up.)

      | Stage | Required input(s) already on disk | If missing, tell the user to run |
      |---|---|---|
      | `analyst` | `migration_from/<source_name>/` exists | add the source repo there |
      | `implementer` | `.cuga-migrator/migration_spec.md` exists | `--stages analyst` first |
      | `test_writer` | at least one `.txt` file under `migration_to/data/ground_truth/` | add ground truth files |
      | `evaluator` | `migration_to/<target_name>/test_cases.json` **and** `migration_spec.md` both exist | `--stages implementer` and/or `--stages test_writer` first |
      | `debugger` | `migration_to/data/prediction/eval_report.json` exists | `--stages evaluator` first |

   b. **For `implementer` only** — also ensure templates are copied first (step 2 of the full
      pipeline above), but only if `migration_to/<target_name>/` doesn't already look scaffolded
      (no `supervisor_config.yaml` / `agent_config.yaml` present yet). If it's already scaffolded,
      leave it alone — don't re-copy raw templates over an implementation already in progress.

   c. **Spawn only that stage's subagent** — `Agent(agent_name="<stage>", prompt="...")` — using
      the exact same inputs listed for that stage in the numbered pipeline above (steps 1/3/4/6a/6b
      respectively). For `debugger` specifically, read `eval_report.json` yourself first to pull
      out the specific failures and iteration number to pass it, same as step 6 does. For
      `evaluator`, after it returns just report the score — do not spawn `debugger` automatically
      unless `debugger` is itself the next stage in the list.

   d. Move to the next stage in the list, if any.

3. **After the last listed stage finishes**, report the combined results and stop.

## State persistence

After each major step, write `.cuga-migrator/state.json`:

```json
{
  "source_name": "<source_name>",
  "target_name": "<target_name>",
  "completed_stages": ["analyst", "implementer"],
  "debug_iterations": 0,
  "overall_score": null
}
```

On resume (if `.cuga-migrator/state.json` exists), read it and skip already-completed stages.
