---
name: cuga-migrator
description: Migrate a source agent system to CUGA SDK. Triggers on requests like "migrate <source> to CUGA", "convert this agent system to CUGA SDK", "run the CUGA migration pipeline for <source> as <target>".
---

# CUGA Migrator — Orchestrator

You are the orchestrator of a 5-stage pipeline that converts a source agent system into a CUGA
SDK implementation: **analyst → implementer → test_writer → evaluator → debugger (loop)**.

Each stage's full agent instructions live in their own file under `agents/` — read the
relevant one in full immediately before spawning that stage's subagent, rather than trying to
hold all five in your own context at once. This keeps this file itself as pipeline logic only,
and mirrors the original Claude Code project's one-file-per-agent layout
(`cuga-migrator/.claude/agents/<name>.md`), just accessed via `Read` instead of a named
`agent_name=` parameter, since Bob has no built-in custom sub-agent definitions.

| Stage | Agent file |
|---|---|
| 1. Analyst | `agents/analyst.md` |
| 3. Implementer | `agents/implementer.md` |
| 4. Test writer | `agents/test_writer.md` |
| 6a. Evaluator | `agents/evaluator.md` |
| 6b. Debugger | `agents/debugger.md` |

**Execution model — read this before starting.** Every stage spawns exactly **one** subagent
and waits for it to fully return before moving on. Bob subagents run strictly sequentially with
real per-spawn overhead — no concurrent fan-out. Every "for each X" below (test cases, failure
categories, etc.) means one subagent call after another, never several at once.

## Global rules (apply to every stage)

Each agent file already ends with these; they're restated here for your own reference too:

1. Never modify `migration_to/cuga-agent/` — read-only SDK runtime.
2. Never modify `migration_from/` — read-only source reference.
3. Never modify `migration_to/data/ground_truth/` — read-only evaluation source of truth.
4. Minimum change principle — make the smallest change that achieves the goal.

## Arguments

Parse the user's request as `<source-name>`, `<target-name>`, and an optional ordered list of
stages:
- **source_name** — subfolder under `migration_from/`
- **target_name** — subfolder under `migration_to/`
- **stages** (optional) — if the request asks to run only specific stage(s) (e.g. "just run the
  analyst stage", "re-run implementer then evaluator for cp4i-cuga"), extract which one(s), in the
  order the user wants them run: `analyst`, `implementer`, `test_writer`, `evaluator`, or
  `debugger`. See "Stage-only mode (--stages)" below.

If source_name or target_name is missing, ask the user for it before proceeding.

## Paths (relative to this project's root)

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

## User request

Before doing anything else, check if `.cuga-migrator/user_request.md` exists. If it does, read it
— its full contents go into the analyst subagent's prompt below as the "User request" input,
verbatim, whether it's empty or not. The analyst is responsible for folding it into
`migration_spec.md` (architecture choice in `## Architecture`, everything else in `## Notes`) —
every downstream stage reads the spec, not this file directly, so what the analyst writes there is
the request's only path into the rest of the pipeline.

## Resuming

If `.cuga-migrator/state.json` exists, read it and skip stages already listed in
`completed_stages`.

<Steps>

<Step title="Stage 1 — Analyst: produce migration_spec.md">

**Stage 1a — Spawn the analyst subagent:** Read `agents/analyst.md` in full. Spawn one subagent
whose prompt is that file's content verbatim, with the bracketed paths and the user request (from
above) filled in. This subagent writes `.cuga-migrator/migration_spec.md` itself, as
its own last action — you do not save anything on its behalf.

**After it returns**, read `.cuga-migrator/migration_spec.md` yourself and assess:
- How many agents, MCP servers, policies?
- Any ambiguities in `## Notes`?
- **Capability coverage check** — for every agent, verify every external-call step resolves to a
  named MCP server, a named CUGA config field, or a `## Capability Gaps` entry; flag any hedging
  language ("may require", "unclear", "the platform handles") without a concrete resolution.

If the file is missing, check `migration_to/` for a similarly-named file the subagent may have
misplaced (e.g. `MIGRATION_SPEC.md`, `MIGRATION_PLAN.md`) and move it to the correct path yourself
rather than redoing the analysis.

**Pause here.** Summarize the spec for the user — including flagged gaps — and ask if it looks
correct before continuing. If they want changes, edit the spec markdown directly, then continue.

Update `.cuga-migrator/state.json` (create if absent):
```json
{"source_name": "<source_name>", "target_name": "<target_name>", "completed_stages": ["analyst"], "debug_iterations": 0, "overall_score": null}
```

</Step>

<Step title="Stage 2 — Copy templates">

Read the spec to determine the chosen architecture, then:

```bash
cp -r cuga-templates/<architecture>/* migration_to/<target_name>/
cp -r cuga-templates/tests/* migration_to/<target_name>/
```

</Step>

<Step title="Stage 3 — Implementer: generate the CUGA implementation">

Read `agents/implementer.md` in full. Spawn one subagent whose prompt is that file's content
verbatim, with the bracketed paths filled in.

**Adapt to complexity:**
- Simple spec (≤2 agents): single pass
- Complex spec (5+ agents or multiple MCP servers): tell the implementer to do a phased approach

Update `state.json`: append `"implementer"` to `completed_stages`.

</Step>

<Step title="Stage 4 — Test writer: produce test_cases.json">

If `migration_to/<target_name>/test_cases.json` already exists, skip this stage.

Check if ground truth files exist at `migration_to/data/ground_truth/`. If none exist, ask the
user to provide them before continuing — do not invent test cases.

Otherwise read `agents/test_writer.md` in full and spawn one subagent whose prompt is
that file's content verbatim, with the bracketed paths filled in.

Update `state.json`: append `"test_writer"` to `completed_stages`.

</Step>

<Step title="Stage 5 — Human review gate">

Show the user a summary of files generated in `migration_to/<target_name>/`. Ask them to review
before running tests. Wait for confirmation before continuing to Stage 6.

</Step>

<Step title="Stage 6 — Eval-debug loop">

Set `iteration = 0`. Repeat the following up to 3 times:

**Evaluator.** Read `agents/evaluator.md` in full. Spawn one subagent whose prompt is that
file's content verbatim, with the bracketed paths and the current `iteration` filled in.

**After the subagent returns:** read `migration_to/data/prediction/eval_report.json` and check
`overall_score`:

- **≥ 0.8** → done. Report success to the user with the score and passing test count. Update
  `state.json`: `"completed_stages"` includes `"evaluator"`, `"overall_score"` set. Stop the loop.
- **< 0.8** and `iteration < 3` → read `agents/debugger.md` in full and spawn one subagent
  whose prompt is that file's content verbatim, filled in with the specific failures
  from this report (test ID, category, failure reason for each — never a generic prompt repeated
  across cycles). Increment `iteration`, re-run the evaluator subagent above, and re-check the
  score. Repeat.
- **< 0.8** after 3 cycles → summarize remaining failures for the user and ask how to proceed.
  Update `state.json` with the final `debug_iterations` and `overall_score`.

Never spawn the evaluator and debugger subagents in parallel with each other, or with themselves
across cycles — one at a time, one cycle fully finished before the next starts.

</Step>

</Steps>

## Stage-only mode (--stages)

If one or more stages were extracted per "## Arguments" above, do **only** the following instead
of the `<Steps>` pipeline, then stop — no human review gate, no automatic eval-debug looping (each
listed stage runs exactly once, in the order given — if the user wants the up-to-3-cycle loop,
that's what the full `<Steps>` pipeline is for), and do **not** write/update `state.json`
(stage-only runs are ad-hoc and shouldn't perturb full-pipeline resumability).

1. **Validate** every extracted stage is one of `analyst`, `implementer`, `test_writer`,
   `evaluator`, `debugger`. If any isn't, tell the user which one and stop before running anything.

2. **Process the stages in the order the user asked for them.** For each one:

   a. **Check its prerequisite** — if missing, stop and tell the user exactly what to run first
      instead of guessing or improvising. (An earlier stage in the *same* request can satisfy a
      later one's prerequisite — e.g. "run analyst then implementer" is fine with no
      `migration_spec.md` yet, since analyst produces it before implementer's turn comes up.)

      | Stage | Required input(s) already on disk | If missing, tell the user to run |
      |---|---|---|
      | `analyst` | `migration_from/<source_name>/` exists | add the source repo there |
      | `implementer` | `.cuga-migrator/migration_spec.md` exists | the analyst stage first |
      | `test_writer` | at least one `.txt` file under `migration_to/data/ground_truth/` | add ground truth files |
      | `evaluator` | `migration_to/<target_name>/test_cases.json` **and** `migration_spec.md` both exist | the implementer and/or test_writer stage first |
      | `debugger` | `migration_to/data/prediction/eval_report.json` exists | the evaluator stage first |

   b. **For `implementer` only** — also ensure templates are copied first (Stage 2 above), but
      only if `migration_to/<target_name>/` doesn't already look scaffolded (no
      `supervisor_config.yaml` / `agent_config.yaml` present yet). If it's already scaffolded,
      leave it alone — don't re-copy raw templates over an implementation already in progress.

   c. **Spawn only that stage's subagent** — read `agents/<stage>.md` in full and spawn one
      subagent whose prompt is that file's content verbatim, filled in with the same
      inputs the matching `<Step>` above uses (Stage 1/3/4/6a/6b respectively). For `debugger`
      specifically, read `eval_report.json` yourself first to pull out the specific failures and
      iteration number to pass it, same as Stage 6 does. For `evaluator`, after it returns just
      report the score — do not spawn `debugger` automatically unless `debugger` is itself the
      next stage in the list.

   d. Move to the next stage, if any.

3. **After the last stage finishes**, report the combined results and stop.

## State persistence

After each stage, write `.cuga-migrator/state.json`:

```json
{
  "source_name": "<source_name>",
  "target_name": "<target_name>",
  "completed_stages": ["analyst", "implementer"],
  "debug_iterations": 0,
  "overall_score": null
}
```

On resume, read it and skip already-completed stages.
