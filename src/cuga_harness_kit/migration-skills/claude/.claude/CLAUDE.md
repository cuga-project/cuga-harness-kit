# CUGA Migrator

This repo migrates source agent systems into CUGA SDK implementations. Five agents run in sequence: `analyst` → `implementer` → `test_writer` → `evaluator` → `debugger`. Each agent is defined in `.claude/agents/<name>.md`. The full pipeline is orchestrated by `.claude/commands/migrate.md`, invoked either via `/migrate <source> <target> [--stages ...]` or in natural language through `.claude/skills/cuga-migrator/SKILL.md` (which parses the request and defers to the same command file). `source_sync` and `cuga_sync` follow the same command+skill pairing.

## Directory layout

```
migration_from/<source-name>/   # source repo (read-only); add CLAUDE.md here for migration hints
migration_to/<target-name>/     # generated CUGA implementation
migration_to/cuga-agent/        # CUGA SDK runtime (read-only)
migration_to/data/
  ground_truth/                 # input .txt trace files (read-only)
  prediction/                   # eval outputs: actual_outputs/, traj/, eval_report.json
  debug_log/                    # debug_<iteration>.md per debug cycle
.cuga-migrator/
  migration_spec.md             # analyst output
  source_summary.md             # analyst intermediate notes
  state.json                    # pipeline progress
cuga-templates/                      # supervisor/, a2a_supervisor_external/, one_agent/, tests/ — canonical CUGA scaffolds
.cuga-migrator/
  user_request.md               # (optional) user's high-level migration intent — read by orchestrator before pipeline starts
```

## Templates — canonical CUGA application structure

Every agent in the pipeline should read the relevant template files before doing their work. Templates define the exact file layout, configuration schema, and code patterns that a valid CUGA application must follow.

### `cuga-templates/supervisor/` — multi-agent supervisor architecture

| File | Purpose |
|------|---------|
| `supervisor_config.yaml` | Declares the supervisor name, model, MCP server registry, and all sub-agent entries (name, description, special_instructions, mcp_servers list, enable_knowledge). This is the primary routing configuration — the supervisor LLM reads agent descriptions to decide which sub-agent to call. Read the constraint comments at the top carefully. |
| `supervisor_entrypoint.py` | Python entrypoint class (`CugaSupervisor`-backed). Reads `supervisor_config.yaml`, loads MCP tools per agent via `MultiServerMCPClient`, constructs each `CugaAgent` (with `enable_knowledge` if set), and wires them into a `CugaSupervisor`. Exposes `create()`, `invoke()`, `stream()`. |
| `mcp_servers/mcp_server_template.py` | FastMCP server stub. One file per external data source. Shows the `@app.tool()` pattern, env-var credential reading, error handling, and SSE entrypoint. Copy and rename for each server in the spec. |
| `.cuga/intent_guards/intent_guard_jailbreak.md` | YAML-frontmatter policy file. Blocks jailbreak and off-topic requests. Shows the `intent_guard` policy format. |
| `.cuga/output_formatters/output_formatter_secrets.md` | YAML-frontmatter policy file. Redacts secrets from agent output. Shows the `output_formatter` policy format. |
| `.cuga/playbooks/playbook_main_workflow.md` | YAML-frontmatter policy file. Step-by-step workflow guidance for the agent's main task. Shows the `playbook` policy format. |
| `.cuga/tool_guides/tool_guide_data_tools.md` | YAML-frontmatter policy file. Documents tool parameters and call-order constraints. Shows the `tool_guide` policy format. |

### `cuga-templates/a2a_supervisor_external/` — CugaSupervisor orchestrating external A2A-wrapped agents

Use this template when the goal is a CugaSupervisor routing to external agents that are independently deployed services (LangGraph, any framework) and exposed via the A2A protocol — not CUGA-native internal agents. The analyst should choose this architecture when `user_request.md` or the source system signals that existing agents should be reused as external services rather than rewritten.

| File | Purpose |
|------|---------|
| `supervisor_config.yaml` | Declares the supervisor with `mcp_servers: []` and all sub-agents as `type: external` with `a2a_protocol` (endpoint, transport, timeout). The supervisor LLM reads agent descriptions for routing. |
| `supervisor_entrypoint.py` | Simplified `CugaSupervisor` entrypoint. No MCP tool loading — iterates agents, registers each A2A-enabled one as `{"type": "external", "config": agent_cfg}`. Exposes `create()`, `invoke()`, `stream()`. |
| `a2a_agents/a2a_agent_template.py` | A2A server stub. Shows the `AgentExecutor` + `AgentCard` + `AgentSkill` + `A2AStarletteApplication` pattern. Copy and rename for each external agent in the spec. |
| `scripts/start.sh` | Starts all A2A agent servers and the CUGA backend. |
| `.cuga/intent_guards/intent_guard_jailbreak.md` | Same `intent_guard` format as supervisor template. |
| `.cuga/output_formatters/output_formatter_secrets.md` | Same `output_formatter` format as supervisor template. |
| `.cuga/playbooks/playbook_main_workflow.md` | Orchestration playbook adapted for A2A delegation (route to external agents, chain results). |
| `.cuga/tool_guides/tool_guide_a2a_delegation.md` | Delegation guide documenting each A2A sub-agent: purpose, when to use, parameters, example call. |

### `cuga-templates/one_agent/` — single-agent architecture

| File | Purpose |
|------|---------|
| `agent_config.yaml` | Declares the MCP server registry. All tools from all servers are loaded into one `CugaAgent`. Read the knowledge engine comment at the top. |
| `agent_entrypoint.py` | Python entrypoint class (`CugaAgent`-backed). Reads `agent_config.yaml`, loads all MCP tools, constructs the agent with `enable_knowledge=True` and `cuga_folder` pointing at `.cuga/`. Exposes `create()`, `invoke()`, `stream()`. |
| `mcp_servers/mcp_server_template.py` | Same FastMCP stub as supervisor template. Copy and rename for each server in the spec. |
| `.cuga/intent_guards/intent_guard_jailbreak.md` | Same `intent_guard` format as supervisor template. |
| `.cuga/output_formatters/output_formatter_secrets.md` | Same `output_formatter` format as supervisor template. |
| `.cuga/playbooks/playbook_main_workflow.md` | Same `playbook` format as supervisor template, adapted for single-agent (calls tools directly, no sub-agent delegation). |
| `.cuga/tool_guides/tool_guide_data_tools.md` | Same `tool_guide` format as supervisor template. |
| `.agents/skills/skill_template/SKILL.md` | Skill definition file. YAML frontmatter with `name` and `description` (used by the agent to pick the right skill), followed by markdown: When to Use, Workflow steps, Output Format, Error Handling. One `SKILL.md` per logical task the agent supports. |

### `cuga-templates/tests/runner_template.py`

Async test runner. Reads `test_cases.json`, instantiates the agent via `Agent.create()`, runs each test case in parallel, writes results to `prediction/actual_outputs/<test_id>.json`. The evaluator fills in the import placeholders before running.

### Policy file format (all types share this structure)

```yaml
---
name: <kebab-case-id>
description: "one-line summary"
type: intent_guard | playbook | output_formatter | tool_guide | tool_approval
enabled: true
id: <snake_case_id>
priority: 50–100
triggers:
  keywords: [keyword1, keyword2]
  case_sensitive: false
  operator: or
  target: intent | output
---

# Policy Title

Markdown body describing the rules, steps, or constraints.
```

Policy files live under `.cuga/<type_plural>/` where the subfolder names are:
`intent_guards/`, `playbooks/`, `output_formatters/`, `tool_guides/`, `tool_approvals/`

## Read-only boundaries

These directories must never be modified by any agent or the orchestrator. They are enforced in each agent definition file.

| Directory | Reason |
|-----------|--------|
| `migration_to/cuga-agent/` | CUGA SDK runtime — shared dependency, not part of any migration output |
| `migration_from/` | Source repo — read-only reference material |
| `migration_to/data/ground_truth/` | Evaluation source of truth — must never be edited to make tests pass |
