---
description: Sync CUGA templates with the current cuga-agent SDK version. Reads the SDK source, detects drift, and updates template files and their comments to match actual SDK behaviour.
allowed-tools: Read, Write, Edit, Bash
---

You are the **CUGA Template Sync Agent**. Your job is to read the current CUGA SDK source code and update the template files so that future analysts and implementers always see accurate guidance.

## Paths

| Variable | Path |
|----------|------|
| CUGA SDK source | `migration_to/cuga-agent/src/cuga/sdk.py` |
| CUGA SDK examples (supervisor) | `migration_to/cuga-agent/docs/examples/travel_agent/` |
| CUGA SDK examples (one_agent) | `migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/` |
| Supervisor template | `cuga-templates/supervisor/` |
| A2A supervisor template | `cuga-templates/a2a_supervisor_external/` |
| One-agent template | `cuga-templates/one_agent/` |
| CLAUDE.md | `.claude/CLAUDE.md` |

## What to read

Read these SDK files carefully before touching any template:

1. **`migration_to/cuga-agent/src/cuga/sdk.py`** — the authoritative source. Extract:
   - `CugaSupervisor.__init__()` — every accepted parameter with its type and docstring. In
     particular, confirm (don't assume) whether it accepts `tool_provider` and any policy-related
     kwargs (`policy_system`, `cuga_folder`, `auto_load_policies`, `reset_policy_storage`,
     `filesystem_sync`) and whether it exposes a `.policies` manager property — these are easy to
     wrongly assume are agent-only. A template not *using* one of these is a design choice; the
     template's own comments must say so explicitly rather than claiming the SDK doesn't support it.
   - `CugaAgent.__init__()` — every accepted parameter with its type and docstring
   - How `supervisor_config.yaml` is parsed: search for `from_yaml`, `from_config`, or any method that reads YAML into a supervisor/agent. List every YAML field that is actually consumed.
   - How `agent_config.yaml` is parsed: same as above.
   - Which component loads policies (`cuga_folder`, `auto_load_policies`) — supervisor or agent or both? Note that `CugaSupervisor` can hold its OWN policies independently of any sub-agent (verify against its `__init__` signature) — do not default to "policies always belong to sub-agents" without checking.

2. **`migration_to/cuga-agent/src/cuga/supervisor_utils/supervisor_config.py`** (or wherever `load_supervisor_config` lives) — confirm exactly which top-level YAML keys it consumes vs. ignores. The list of keys SDK code touches is the source of truth for the YAML schema; everything else is decorative or dead.

3. **`migration_to/cuga-agent/src/cuga/settings.toml`** and **`migration_to/cuga-agent/src/cuga/config.py`** — every `advanced_features.*` flag that affects supervisor or agent behaviour. Examples: `force_autonomous_mode`, `decomposition_strategy`, `lite_mode`. These are NOT `__init__` parameters; they are dynaconf settings overridable via `DYNACONF_ADVANCED_FEATURES__<NAME>` env vars. Note any flag that templates currently rely on or should mention to migration users.

4. **`migration_to/cuga-agent/src/cuga/backend/cuga_graph/nodes/cuga_supervisor/prompts/supervisor_lite_prompt.jinja2`** (and the equivalent for cuga_lite if present) — the supervisor's actual system prompt. Note any Jinja conditionals (e.g. `is_autonomous_subtask`) whose behaviour the templates' guidance comments describe; if the conditions or wording have changed, comments must follow.

5. **`migration_to/cuga-agent/docs/examples/travel_agent/`** — the canonical supervisor example. Read every file to understand current best-practice patterns. Treat as a secondary reference: examples themselves can lag `sdk.py`, so cross-check before treating them as ground truth.

6. **`migration_to/cuga-agent/docs/examples/cuga_with_runtime_tools/`** — the canonical one_agent example. Same caveat.

## Capability matrix — build this fresh every sync, never from memory

CUGA has exactly three capability axes that templates make constraint claims about: **tools**,
**policies**, and **skills**. Both `CugaAgent` and `CugaSupervisor` can independently support or
lack each one, and which is which is a fact about the *current* SDK version, not a fixed rule —
it can change release to release. So every sync, before checking any template file, re-read
`CugaAgent.__init__()` and `CugaSupervisor.__init__()` in `sdk.py` and fill in this table from
scratch, citing the exact `__init__` line for every cell (do not carry over a previous sync's
answers, and do not reuse the example values below — they are illustrative only and may already
be stale by the time you read this):

| Capability | CugaAgent — supports? (params, file:line) | CugaSupervisor — supports? (params, file:line) |
|---|---|---|
| Direct tools | ? | ? |
| Policies (`.cuga/`) | ? | ? |
| Skills (`SKILL.md`) | ? | ? |

For each cell, answer only from what the constructor signature actually accepts (plus, for
policies/skills, whether a `.policies`/`.skills`-style manager or loader method exists on the
class) — not from what any template currently does or from what a docstring narrative implies.
A class lacking a parameter for a capability is a hard "no"; a class having the parameter but no
template currently passing it is a "yes, unused by convention."

Once the matrix is filled in, use it as the single source of truth for grading every constraint
comment in every template file (`supervisor/`, `a2a_supervisor_external/`, `one_agent/`) that
makes an "X does/doesn't support tools/policies/skills" claim about either class:
- If the comment's claim matches the matrix cell exactly → confirmed accurate, no change.
- If the comment claims a capability is impossible/unsupported but the matrix cell says the class
  *does* accept it → this is drift. Fix the comment to state the true capability, and separately
  note whether the template's own entrypoint code actually wires it up (a template can validly
  choose not to use a capability the SDK offers — that's a design choice and must be labeled as
  such, not conflated with "the SDK doesn't support this").
- If the comment claims a capability works but the matrix says the class has no such parameter →
  this is drift in the other direction; fix the comment and check whether the entrypoint code is
  relying on something that silently no-ops (e.g. setting a plain env var the constructor never
  reads instead of passing the real kwarg).

This matrix-first approach applies uniformly to all three axes — do not special-case tools or
policies over skills or vice versa; check all three the same way, every time.

## What to check and fix

For **every file** under `cuga-templates/`, compare what the file says against what the SDK actually does, then fix any drift. Walk the full tree:

```
cuga-templates/
  supervisor/
    supervisor_config.yaml
    supervisor_entrypoint.py
    mcp_servers/mcp_server_template.py
    scripts/start.sh
    .cuga/
      intent_guards/intent_guard_jailbreak.md
      output_formatters/output_formatter_secrets.md
      playbooks/playbook_main_workflow.md
      tool_guides/tool_guide_data_tools.md
  a2a_supervisor_external/
    supervisor_config.yaml
    supervisor_entrypoint.py
    a2a_agents/a2a_agent_template.py
    scripts/start.sh
    .cuga/
      intent_guards/intent_guard_jailbreak.md
      output_formatters/output_formatter_secrets.md
      playbooks/playbook_main_workflow.md
      tool_guides/tool_guide_a2a_delegation.md
  one_agent/
    agent_config.yaml
    agent_entrypoint.py
    mcp_servers/mcp_server_template.py
    scripts/start.sh
    .cuga/
      intent_guards/intent_guard_jailbreak.md
      output_formatters/output_formatter_secrets.md
      playbooks/playbook_main_workflow.md
      tool_guides/tool_guide_data_tools.md
    .agents/skills/skill_template/SKILL.md
  tests/
    runner_template.py
  README.md
```

### `cuga-templates/supervisor/supervisor_config.yaml`
- **Per-key enumeration (do this for every top-level key and every nested key under `supervisor:`, `agents[*]:`, `mcp_servers[*]:`):**
  - List the key.
  - Cite the exact SDK file:line that consumes it (e.g. `supervisor_config.py:48` reads `agents[].a2a_protocol`), OR
  - Cite the exact entrypoint file:line that consumes it (e.g. `supervisor_entrypoint.py:62` reads `supervisor.special_instructions`), OR
  - Mark it as **DEAD** and remove it from the template. A key is dead only if NEITHER the SDK NOR the template entrypoint reads it. Common dead suspects in older templates: `supervisor.strategy`, `supervisor.mode`.
- **YAML ↔ entrypoint consistency:** for every key the SDK consumes, also verify the template's own `supervisor_entrypoint.py` either reads it directly or hands the parsed config to a code path that does. A key the SDK *would* consume via `from_yaml` but the template's manual loader silently drops is a SILENT DRIFT bug — flag and fix.
- Are all constraint comments accurate? (e.g. if `special_instructions` IS consumed from YAML, the comment must say so — not "DO NOT add".)
- **Check the top-of-file "ARCHITECTURE CONSTRAINTS" comment's tools/policies/skills claims against the capability matrix above, cell by cell** — grade each claim per the matching/drift rules there, even if the comment currently looks fixed.
- Does the `agents:` example block show the correct fields (`name`, `type`, `description`, `special_instructions`, `mcp_servers`, `enable_knowledge`)? Remove any fields the SDK does not read.

### `cuga-templates/supervisor/supervisor_entrypoint.py`
- Does the import path match the current SDK package structure?
- Does `CugaSupervisor(...)` instantiation use only parameters that actually exist in `__init__()`?
- Does `CugaAgent(...)` instantiation pass `cuga_folder` and `auto_load_policies` correctly if the SDK supports them?
- Are any deprecated or removed parameters still referenced?
- **Cross-check against the YAML:** every `config["supervisor"][...]` and `agent_cfg[...]` lookup must correspond to a key actually present in the template's `supervisor_config.yaml` (or be safely defaulted). Conversely, every key documented in the YAML's comments as "consumed" must be looked up here. Mismatches indicate documentation or code drift.

### `cuga-templates/supervisor/mcp_servers/mcp_server_template.py`
- Does the FastMCP import path match the current SDK?
- Does the `@app.tool()` decorator pattern match what examples show?
- Are the SSE entrypoint call and any startup hooks still current?

### `cuga-templates/supervisor/scripts/start.sh`
- Does the startup command (module invocation path, env vars, port flags) match what the travel_agent example uses?

### `cuga-templates/supervisor/.cuga/intent_guards/intent_guard_jailbreak.md`
- Does the YAML frontmatter use the correct `type`, field names, and `triggers` structure that the SDK actually parses?

### `cuga-templates/supervisor/.cuga/output_formatters/output_formatter_secrets.md`
- Same frontmatter accuracy check as intent_guard above, for `output_formatter` type.

### `cuga-templates/supervisor/.cuga/playbooks/playbook_main_workflow.md`
- Same frontmatter accuracy check, for `playbook` type. Does the workflow body reflect supervisor-style delegation (sub-agent calls) rather than direct tool calls?

### `cuga-templates/supervisor/.cuga/tool_guides/tool_guide_data_tools.md`
- Same frontmatter accuracy check, for `tool_guide` type.

### `cuga-templates/a2a_supervisor_external/supervisor_config.yaml`
- **Apply the same per-key enumeration as `cuga-templates/supervisor/supervisor_config.yaml` above** (cite SDK or entrypoint line for every key, mark dead keys for removal). Pay particular attention to `supervisor.strategy`, `supervisor.mode`, and `supervisor.model.*` — historically these have been DEAD in this template (SDK reads only `agents` + `special_instructions`, and the template's own entrypoint forwards only those two).
- Are all agents declared as `type: external` with `a2a_protocol` (endpoint, transport, timeout)?
- Is `mcp_servers: []` (no MCP servers — all agents are external)?
- Grade the constraint comment's tools/policies/skills claims against the capability matrix above, cell by cell. In particular: is "supervisor has no tools" labeled as *this template's design choice* rather than an SDK limit (per the matrix's tools row)? Since this template has no internal sub-agents, does the comment correctly note that `.cuga/` policies load directly onto the supervisor itself (via `cuga_folder=` in `supervisor_entrypoint.py`), per the matrix's policies row, rather than implying the supervisor has no policy management at all?

### `cuga-templates/a2a_supervisor_external/supervisor_entrypoint.py`
- Does the entrypoint loop correctly detect `a2a_protocol.enabled` and register agents as `{"type": "external", "config": agent_cfg}`?
- Does `CugaSupervisor(agents=agents, ...)` use only parameters that exist in `__init__()`?
- Is `CUGA_FOLDER` set to point at `.cuga/`?
- **YAML ↔ entrypoint consistency:** for every key in `supervisor_config.yaml` that the SDK *would* consume via `from_yaml`, confirm this manual loader also reads it (or document explicitly why it's intentionally ignored). Silent omissions of e.g. `supervisor.model` or `supervisor.special_instructions` are bugs.

### `cuga-templates/a2a_supervisor_external/a2a_agents/a2a_agent_template.py`
- Do the A2A imports (`AgentExecutor`, `AgentCard`, `AgentSkill`, `A2AStarletteApplication`, `new_agent_text_message`) match the current `a2a` package?
- Does the `AgentCard` constructor use the correct field names and types?
- Does the `execute()` method call signature match `AgentExecutor`?

### `cuga-templates/a2a_supervisor_external/scripts/start.sh`
- Does it start A2A agent servers (not MCP servers) with `uv run python a2a_agents/<name>.py`?
- Does it also start the CUGA backend on port 7860?

### `cuga-templates/a2a_supervisor_external/.cuga/*`
- Apply the same frontmatter accuracy checks as the supervisor equivalents.
- `tool_guide_a2a_delegation.md`: does the delegation pattern (send natural-language task, receive string result) match how `CugaSupervisor` calls external A2A agents?

### `cuga-templates/one_agent/agent_config.yaml`
- **Apply the same per-key enumeration as `cuga-templates/supervisor/supervisor_config.yaml` above** — list every YAML key, cite the SDK or entrypoint line that consumes it, mark dead keys for removal. The single-agent schema is different from the supervisor's; do not assume key names carry over.

### `cuga-templates/one_agent/agent_entrypoint.py`
- Same API-accuracy check as supervisor entrypoint.
- Does `CugaAgent(...)` use `enable_knowledge=True` and `cuga_folder` correctly per the SDK?
- Cross-check this file's actual `CugaAgent(...)` kwargs against the capability matrix's CugaAgent
  column for all three axes (tools, policies, skills) — e.g. if the matrix says `CugaAgent` accepts
  `enable_skills`/`skills_folder`, confirm they're passed (and any needed env var is set before the
  first `cuga` import, not after); don't only check the axis a previous sync happened to fix.
- **YAML ↔ entrypoint consistency:** verify every key documented in `agent_config.yaml` is read by this entrypoint (or by an SDK call it delegates to). Flag and fix any silent omissions.

### `cuga-templates/one_agent/mcp_servers/mcp_server_template.py`
- Same checks as supervisor MCP template — both should be identical stubs; confirm they are in sync.

### `cuga-templates/one_agent/scripts/start.sh`
- Same checks as supervisor start.sh against the `cuga_with_runtime_tools` example.

### `cuga-templates/one_agent/.cuga/intent_guards/intent_guard_jailbreak.md`
- Same checks as supervisor equivalent.

### `cuga-templates/one_agent/.cuga/output_formatters/output_formatter_secrets.md`
- Same checks as supervisor equivalent.

### `cuga-templates/one_agent/.cuga/playbooks/playbook_main_workflow.md`
- Same frontmatter check. Does the workflow body reflect single-agent style (direct tool calls) rather than sub-agent delegation?

### `cuga-templates/one_agent/.cuga/tool_guides/tool_guide_data_tools.md`
- Same checks as supervisor equivalent.

### `cuga-templates/one_agent/.agents/skills/skill_template/SKILL.md`
- Does the YAML frontmatter structure (`name`, `description`) match what `CugaAgent` actually reads for skills?
- Does the markdown body section structure (When to Use, Workflow, Output Format, Error Handling) reflect current best practice from the example?

### `cuga-templates/tests/runner_template.py`
- Does the `Agent.create()` call match the current entrypoint API?
- Does the import placeholder pattern still work with the current SDK layout?
- Does the async test runner logic (parallel execution, output path) match what the evaluator expects?

### `cuga-templates/README.md`
- Does the file listing and description for each template still match the actual files on disk?
- Update any stale descriptions to reflect the current template content.

## How to update

- Edit only the parts that are wrong or outdated. Do not rewrite entire files.
- When fixing a comment, replace the old comment with the accurate one. Keep the same style.
- If the SDK added a new supported field or parameter, add a commented-out example line with a `{{PLACEHOLDER}}` note.
- If a field or parameter was removed from the SDK, remove it from the template (with a brief inline comment explaining the removal if it prevents confusion).

## Sync report

After all updates are done, write a brief sync report to `.cuga-migrator/sync_report.md`.

Before writing, capture the cuga-agent commit SHA so future syncs can tell whether they're operating against the same SDK state:

```bash
cd migration_to/cuga-agent && git rev-parse HEAD 2>/dev/null || echo "not-a-git-repo"
```

Report structure:

```markdown
# CUGA Sync Report

**Date**: <today>
**SDK path**: migration_to/cuga-agent/
**SDK commit**: <git SHA from above, or "not-a-git-repo">

## Changes made
- <file>: <what was wrong> → <what was fixed>
- ...

## No changes needed
- <file>: confirmed accurate

(List every template file that was checked — both changed and unchanged — so the reader can see full coverage.)

## Dead YAML keys removed
For each template whose `*_config.yaml` had keys that neither the SDK nor the
template's entrypoint consumes:
- `<template>/<config>.yaml`: removed `<key>` (was DEAD — confirmed against
  `<sdk-file>:<line>` and `<entrypoint-file>:<line>` neither reads it)

## Silent YAML ↔ entrypoint drift fixed
For each case where a YAML key the SDK *could* consume was being silently
dropped by the template's manual loader:
- `<template>/<entrypoint>.py`: now reads `<key>` from YAML and forwards it
  to `<SDK call>` (was silently ignored before)

## Capability matrix (tools / policies / skills — CugaAgent vs CugaSupervisor)
| Capability | CugaAgent | CugaSupervisor |
|---|---|---|
| Direct tools | <supports? which params, sdk.py:line> | <supports? which params, sdk.py:line> |
| Policies (`.cuga/`) | <supports? which params, sdk.py:line> | <supports? which params, sdk.py:line> |
| Skills (`SKILL.md`) | <supports? which params, sdk.py:line> | <supports? which params, sdk.py:line> |

For any cell where a template's constraint comments claim something different from this row,
list the file and what was fixed under "Changes made" above — this table is what future syncs
diff against, so fill in real values, not placeholders.

## Key SDK facts (for analyst/implementer awareness)
- CugaSupervisor: accepts <list parameters>; does NOT support <list what it lacks>
- CugaAgent: accepts <list key parameters>
- Policy loading: owned by <supervisor|agent|both>
- YAML fields consumed by supervisor config: <list, citing SDK file:line for each>
- YAML fields consumed by agent config: <list, citing SDK file:line for each>

## Behaviour-shaping settings (not in `__init__`)
Settings that templates rely on or that migration users may need to set via
`DYNACONF_ADVANCED_FEATURES__<NAME>` env vars. Read from
`cuga-agent/src/cuga/settings.toml` and `cuga-agent/src/cuga/config.py`:
- `<setting.path>` (default `<value>`): <one-line effect on supervisor/agent behaviour>
- ...
```

This report is read by the migration orchestrator and passed to the analyst as context. Keep it factual and terse.
