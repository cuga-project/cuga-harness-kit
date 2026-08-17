---
name: cuga-template-sync
description: Use when the CUGA SDK (migration_to/cuga-agent/) has been updated and templates need to be checked for drift before the next migration. Triggers on requests like "sync CUGA templates", "check templates against the SDK", "update templates for the new CUGA SDK version".
---

# CUGA Template Sync

Read the current CUGA SDK source and update `cuga-templates/` so future `cuga-migrator` runs produce
accurate implementations. Run this whenever `migration_to/cuga-agent/` is updated to a new SDK
version — before starting a migration.

## Paths

| Variable | Path |
|----------|------|
| CUGA SDK source | `migration_to/cuga-agent/src/cuga/sdk.py` |
| CUGA SDK examples (supervisor) | `migration_to/cuga-agent/docs/examples/travel_agent/` |
| CUGA SDK examples (one_agent) | `migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/` |
| Supervisor template | `cuga-templates/supervisor/` |
| A2A supervisor template | `cuga-templates/a2a_supervisor_external/` |
| One-agent template | `cuga-templates/one_agent/` |

<Steps>

<Step title="1. Read the SDK source carefully before touching any template">

1. **`migration_to/cuga-agent/src/cuga/sdk.py`** — the authoritative source. Extract every
   accepted parameter (with type + docstring) of `CugaSupervisor.__init__()` and
   `CugaAgent.__init__()`. In particular, confirm (don't assume) whether `CugaSupervisor`
   accepts `tool_provider` and any policy-related kwargs (`policy_system`, `cuga_folder`,
   `auto_load_policies`, `reset_policy_storage`, `filesystem_sync`) and exposes a `.policies`
   manager property — these are easy to wrongly assume are agent-only. Find how
   `supervisor_config.yaml` / `agent_config.yaml` are parsed — list every YAML field actually
   consumed. Determine which component loads policies (`cuga_folder`, `auto_load_policies`) —
   note that `CugaSupervisor` can hold its OWN policies independently of any sub-agent; don't
   default to "policies always belong to sub-agents" without checking.
2. **`.../supervisor_utils/supervisor_config.py`** (or wherever `load_supervisor_config` lives) —
   confirm exactly which top-level YAML keys it consumes vs. ignores. This is the source of truth
   for the YAML schema.
3. **`.../src/cuga/settings.toml`** and **`.../src/cuga/config.py`** — every
   `advanced_features.*` flag affecting supervisor/agent behaviour (e.g.
   `force_autonomous_mode`, `decomposition_strategy`, `lite_mode`). These are dynaconf settings,
   not `__init__` parameters, overridable via `DYNACONF_ADVANCED_FEATURES__<NAME>` env vars.
4. **`.../prompts/supervisor_lite_prompt.jinja2`** — the supervisor's actual system prompt. Note
   any Jinja conditionals whose behaviour the templates' guidance comments describe.
5. **`docs/examples/travel_agent/`** and **`docs/examples/cuga_with_runtime_tools/`** — canonical
   examples. Treat as secondary references: they can lag `sdk.py`, cross-check before trusting.

</Step>

<Step title="1b. Capability matrix — build this fresh every sync, never from memory">

CUGA has exactly three capability axes that templates make constraint claims about: **tools**,
**policies**, and **skills**. Both `CugaAgent` and `CugaSupervisor` can independently support or
lack each one, and which is which is a fact about the *current* SDK version, not a fixed rule —
it can change release to release. Before checking any template file, re-read
`CugaAgent.__init__()` and `CugaSupervisor.__init__()` in `sdk.py` and fill in this table from
scratch, citing the exact `__init__` line for every cell (do not carry over a previous sync's
answers):

| Capability | CugaAgent — supports? (params, file:line) | CugaSupervisor — supports? (params, file:line) |
|---|---|---|
| Direct tools | ? | ? |
| Policies (`.cuga/`) | ? | ? |
| Skills (`SKILL.md`) | ? | ? |

For each cell, answer only from what the constructor signature actually accepts (plus, for
policies/skills, whether a `.policies`-style manager or loader method exists) — not from what any
template currently does. A class lacking a parameter for a capability is a hard "no"; a class
having the parameter but no template currently passing it is a "yes, unused by convention."

Use the finished matrix as the single source of truth for grading every constraint comment in
every template file that makes an "X does/doesn't support tools/policies/skills" claim: matches →
confirmed accurate; comment says impossible but matrix says supported → rewrite the comment to
plainly state, in your own words based on what you verify that sync, what the template currently
has configured for that capability and — if unused — which kwarg would turn it on (and check
whether the entrypoint silently relies on something that no-ops, e.g. a plain env var the
constructor never reads instead of the real kwarg); comment says supported but matrix says no such
param → fix the comment the other direction. State only the fact you just verified from the live
SDK/template that sync — never frame it as "a design choice, not an SDK limitation," and don't
reference what the comment used to say; that kind of before/after narrative belongs in the sync
report, not the template file. Apply this the same way to all three axes — don't special-case
tools or policies over skills.

</Step>

<Step title="2. Check every file under cuga-templates/ for drift">

For each `*_config.yaml` (supervisor, a2a_supervisor_external, one_agent): enumerate every
top-level and nested key, cite the exact SDK or entrypoint file:line that consumes it, or mark it
**DEAD** and remove it (dead only if neither the SDK nor the template's own entrypoint reads it —
common dead suspects: `supervisor.strategy`, `supervisor.mode`). Verify YAML ↔ entrypoint
consistency both directions — a key the SDK would consume via `from_yaml` but the template's
manual loader silently drops is a silent-drift bug; fix it. Confirm constraint comments are
accurate (e.g. if `special_instructions` IS consumed, the comment must say so, not "DO NOT add").
Grade any tools/policies/skills capability claim against the matrix above, cell by cell.

For each `*_entrypoint.py`: import paths match current SDK package structure; constructor calls
use only parameters that actually exist; no deprecated/removed parameters referenced; every
config lookup corresponds to a key actually present in that template's YAML.

For each `mcp_servers/mcp_server_template.py` / `a2a_agents/a2a_agent_template.py`: import paths,
decorator/class patterns, and entrypoint calls match current SDK/A2A package versions.

For each `scripts/start.sh`: startup commands (module path, env vars, ports) match the canonical
example.

For each `.cuga/<type>/*.md` policy template: YAML frontmatter uses the field names and
`triggers` structure the SDK actually parses for that `type`.

For `cuga-templates/one_agent/.agents/skills/skill_template/SKILL.md`: frontmatter (`name`,
`description`) matches what `CugaAgent` reads for skills; body section structure (When to Use,
Workflow, Output Format, Error Handling) reflects current best practice.

For `cuga-templates/tests/runner_template.py`: `Agent.create()` call matches the current entrypoint
API; import placeholder pattern still works; parallel-execution/output-path logic matches what
the evaluator stage expects.

For `cuga-templates/README.md`: file listing and descriptions still match what's actually on disk.

</Step>

<Step title="3. Update — minimal, targeted edits">

Edit only the parts that are wrong or outdated; do not rewrite entire files. When fixing a
comment, replace it with one that plainly states the current, correct fact — a reader opening the
template fresh should see only accurate, present-tense documentation of what it does now, not
"previously this said...", "this used to be...", or "design choice vs SDK limitation" narration.
Keep any before/after story in the sync report. If the SDK added a new field, add a commented-out
example line with a `{{PLACEHOLDER}}` note. If a field was removed, remove it (with a brief inline
comment explaining the removal if it prevents confusion).

</Step>

<Step title="4. Write the sync report">

First capture the SDK commit so future syncs can tell whether they're operating against the same
state:

```bash
cd migration_to/cuga-agent && git rev-parse HEAD 2>/dev/null || echo "not-a-git-repo"
```

Write `.cuga-migrator/sync_report.md`:

```markdown
# CUGA Sync Report

**Date**: <today>
**SDK path**: migration_to/cuga-agent/
**SDK commit**: <git SHA or "not-a-git-repo">

## Changes made
- <file>: <what was wrong> -> <what was fixed>

## No changes needed
- <file>: confirmed accurate

## Dead YAML keys removed
- `<template>/<config>.yaml`: removed `<key>` (confirmed dead against `<sdk-file>:<line>` and `<entrypoint-file>:<line>`)

## Silent YAML <-> entrypoint drift fixed
- `<template>/<entrypoint>.py`: now reads `<key>` from YAML and forwards it to `<SDK call>` (was silently ignored before)

## Key SDK facts (for cuga-migrator awareness)
- CugaSupervisor: accepts <parameters>; does NOT support <what it lacks>
- CugaAgent: accepts <key parameters>
- Policy loading: owned by <supervisor|agent|both>
- YAML fields consumed by supervisor config: <list, citing SDK file:line>
- YAML fields consumed by agent config: <list, citing SDK file:line>

## Behaviour-shaping settings (not in __init__)
- `<setting.path>` (default `<value>`): <one-line effect>
```

This report is read by the migration orchestrator and passed to the analyst as context. Keep it
factual and terse — list every template file checked, both changed and unchanged, so coverage is
visible.

</Step>

</Steps>
