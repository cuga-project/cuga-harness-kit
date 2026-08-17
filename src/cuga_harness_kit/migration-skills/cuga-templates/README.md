# Templates

These are CUGA output scaffolds that define the exact structure of a valid CUGA application.

## Placeholder convention

Every value that must be replaced by the implementer is marked with a comment:
```
# {{PLACEHOLDER: description of what goes here}}
```

The implementer reads the migration spec and replaces all placeholders with values derived from it.

## Directory structure

```
cuga-templates/
├── supervisor/                          # Multi-agent supervisor architecture (CugaSupervisor + MCP sub-agents)
│   ├── supervisor_config.yaml           # Supervisor + sub-agent declarations (see ARCHITECTURE CONSTRAINT comment)
│   ├── supervisor_entrypoint.py         # CugaSupervisor entrypoint; reads config, wires agents + MCP tools
│   ├── mcp_servers/
│   │   └── mcp_server_template.py       # FastMCP server stub — one file per external data source
│   ├── scripts/
│   │   └── start.sh                     # Starts all MCP servers and the CUGA backend
│   └── .cuga/                           # Policy files loaded at runtime (onto sub-agents)
│       ├── intent_guards/
│       │   └── intent_guard_jailbreak.md
│       ├── playbooks/
│       │   └── playbook_main_workflow.md
│       ├── output_formatters/
│       │   └── output_formatter_secrets.md
│       └── tool_guides/
│           └── tool_guide_data_tools.md
├── a2a_supervisor_external/             # CugaSupervisor orchestrating external agents wrapped by A2A
│   ├── supervisor_config.yaml           # Supervisor with type:external agents using a2a_protocol (no mcp_servers)
│   ├── supervisor_entrypoint.py         # Simplified CugaSupervisor entrypoint; registers A2A agents only
│   ├── a2a_agents/
│   │   └── a2a_agent_template.py        # A2A server stub — one file per external agent
│   ├── scripts/
│   │   └── start.sh                     # Starts all A2A agent servers and the CUGA backend
│   └── .cuga/                           # Policy files (same types as supervisor/, adapted for A2A context)
│       ├── intent_guards/
│       │   └── intent_guard_jailbreak.md
│       ├── playbooks/
│       │   └── playbook_main_workflow.md
│       ├── output_formatters/
│       │   └── output_formatter_secrets.md
│       └── tool_guides/
│           └── tool_guide_a2a_delegation.md
├── one_agent/                           # Single-agent architecture (CugaAgent + skills)
│   ├── agent_config.yaml                # MCP server registry
│   ├── agent_entrypoint.py              # CugaAgent entrypoint; loads all tools, enable_knowledge=True, enable_skills=True
│   ├── mcp_servers/
│   │   └── mcp_server_template.py       # FastMCP server stub — one file per external data source
│   ├── scripts/
│   │   └── start.sh                     # Starts all MCP servers required by the agent
│   ├── .cuga/                           # Policy files loaded at runtime
│   │   ├── intent_guards/
│   │   │   └── intent_guard_jailbreak.md
│   │   ├── playbooks/
│   │   │   └── playbook_main_workflow.md
│   │   ├── output_formatters/
│   │   │   └── output_formatter_secrets.md
│   │   └── tool_guides/
│   │       └── tool_guide_data_tools.md
│   └── .agents/skills/
│       └── skill_template/
│           └── SKILL.md                 # Skill definition — one per logical task the agent supports
└── tests/
    └── runner_template.py               # Async test runner; reads test_cases.json, runs eval
```

## Key constraints (encoded in the template files themselves)

- **`CugaSupervisor` CAN have its own direct tools** — `CugaSupervisor.__init__` accepts a
  `tool_provider=` kwarg (a `ToolProviderInterface`, not a `tools=` list; `sdk.py:2971-3048`).
  Tools from it are exposed to the supervisor LLM and made directly callable exactly like
  `delegate_to_<agent>()` functions (`cuga_supervisor/nodes/prepare_agents_and_prompt.py:222-236`).
  **Neither `supervisor/` nor `a2a_supervisor_external/` wires this up** — both templates
  route 100% of tool access through sub-agents. To give the supervisor itself directly
  callable tools, pass `tool_provider=` to `CugaSupervisor(...)` in
  `supervisor_entrypoint.py` rather than adding a new sub-agent.

- **Sub-agent tool configuration (internal agents)** — each agent entry in `supervisor_config.yaml`
  can declare its own tools via any of these keys (processed by `load_supervisor_config`):
  - `mcp_servers: [...]` — list of MCP server configs loaded directly for this agent
  - `apps: [...]` — app names resolved via the CUGA tool registry
  - `tools: [...]` — direct LangChain tool references (limited YAML support; prefer Python)
  - `model: {provider, model_name}` — per-agent model override
  - `import_from: module.path.agent_var` — import a fully pre-configured `CugaAgent` from Python;
    use this when the agent needs tools, policies, or config that can't be expressed in YAML

- **A2A vs MCP sub-agents** — use `a2a_supervisor_external/` when the goal is CugaSupervisor
  orchestrating external agents that are independently deployed and wrapped by the A2A protocol
  (LangGraph, custom HTTP, any framework). Use `supervisor/` when sub-agents are CUGA-native
  internal agents configured via YAML.

- **A2A agent registration** — set `type: external` and `a2a_protocol.enabled: true` in the
  agent entry; `load_supervisor_config` (or the entrypoint) registers it as
  `{"type": "external", "config": agent_cfg}` in `CugaSupervisor`.

- **Knowledge base / RAG → `enable_knowledge`** — see comment in `supervisor/supervisor_config.yaml`
  and `one_agent/agent_config.yaml`. Use CUGA's native knowledge engine instead of a custom MCP server.

- **MCP servers** — one `mcp_servers/*.py` file per external data source. Use `mcp_server_template.py`
  as the starting point. Register each server in `*_config.yaml` with its SSE URL and port.

- **Policies** — live in `.cuga/<type_plural>/`. Types: `intent_guards`, `playbooks`,
  `output_formatters`, `tool_guides`, `tool_approvals`. See existing examples for the YAML frontmatter format.

- **Skills gotcha (`one_agent/` only)** — `SKILL.md` files are OFF by default
  (`settings.skills.enabled = false`) and, even when enabled, are discovered from
  `.cuga/skills/` by default (`settings.skills.root = "cuga"`), NOT `.agents/skills/`
  where `skill_template/` lives. `agent_entrypoint.py` must set both
  `enable_skills=True` on `CugaAgent(...)` *and* `DYNACONF_SKILLS__ROOT=agents`
  **before the first `cuga` import** (dynaconf resolves `DYNACONF_*` env vars at
  Settings-construction time, not per-access — setting it inside `create()` is too
  late). Both are already wired in the template; don't remove them.
