---
name: cuga-author-policy
description: Use when the user wants to govern agent behavior with a cuga policy - block/redirect an intent, add step-by-step playbook guidance, require approval before a tool runs, enhance a tool's description, or reshape agent output format.
---

# Authoring a cuga policy

A cuga **policy** is a rule the runtime enforces on a `CugaAgent`, unlike a runtime *skill* (`cuga-build-cuga-skill`) which the agent optionally chooses to load. There are 5 policy types.

## Step 1 — identify which type

| The user wants to... | Type |
|---|---|
| Block or redirect a specific kind of request | `intent_guard` |
| Give the agent step-by-step guidance for a workflow | `playbook` |
| Require human approval before a tool runs | `tool_approval` |
| Add usage guidance/examples to a tool's description | `tool_guide` |
| Reshape the agent's response into JSON/table/markdown/etc. | `output_formatter` |

## Step 2 — pick programmatic SDK or markdown file

**Programmatic (recommended for code you already control):** attach at agent construction time via `agent.policies`:

```python
await agent.policies.add_intent_guard(
    name="Block Delete Operations",
    description="Prevents deletion of critical data",
    keywords=["delete", "remove", "erase"],
    response="Deletion operations are not permitted for security reasons.",
    priority=100,  # higher = checked first
)

await agent.policies.add_playbook(
    name="Budget Analysis Workflow",
    description="Multi-step process for analyzing financial budgets",
    natural_language_trigger=["When user asks to analyze their budget"],
    content="# Budget Analysis Workflow\n\n## Step 1: ...",
    priority=50,
)
```

**Markdown file (for the `manager` web UI, or policies you want checked into a project):** save a file with YAML frontmatter + markdown body to the matching `.cuga/` subfolder, then restart or re-publish so it's picked up:

| Type | Save to |
|---|---|
| `playbook` | `.cuga/playbooks/playbook_<name>.md` |
| `intent_guard` | `.cuga/guards/guard_<name>.md` |
| `tool_guide` | `.cuga/guides/guide_<name>.md` |
| `tool_approval` | `.cuga/approvals/approval_<name>.md` |
| `output_formatter` | `.cuga/formatters/formatter_<name>.md` |

Shared frontmatter fields across all 5 types: `id`, `name`, `description`, `enabled`, `priority`, `type`, `triggers` (shape varies by type — see below).

## Mode: Playbook

```yaml
---
description: Brief description of what this playbook does
enabled: true
id: playbook_<unique_id>
name: <Playbook Name>
priority: 50
triggers:
  natural_language:
  - keyword 1
  - keyword phrase
  target: intent
  threshold: 0.5
type: playbook
---
# <Title>
## Overview
## Parameters
- **parameter_name** (required/optional): description
## Steps
### 1. <Step Name> — constraints: MUST / SHOULD / MAY
## Examples
## Troubleshooting
## Best Practices
```

## Mode: Intent Guard

```yaml
---
description: Description of what intents this guard blocks
enabled: true
id: guard_<unique_id>
name: <Guard Name>
priority: 90        # 90-100 recommended: guards should win priority ties
triggers:
  natural_language:
  - blocked intent 1
  target: intent
  threshold: 0.7     # strict matching for guards
type: intent_guard
intent_examples:
- 5+ example phrases of the blocked intent, for matching
response:
  response_type: natural_language   # natural_language | json | template
  content: |
    Custom message explaining why this is blocked + alternatives.
allow_override: false   # true = user can bypass, false = enforced
---
```

## Mode: Tool Guide

```yaml
---
description: Enhanced guidance for specific tools
enabled: true
id: guide_<unique_id>
name: <Guide Name>
priority: 50
triggers:
  tool_match:
  - tool_name_1
  target: tools
type: tool_guide
target_tools: [tool_name_1, tool_name_2]   # or target_apps: [app_name] for all tools in an app
guide_content: |
  ## When to Use / Best Practices / Common Pitfalls / Parameter Guidelines / Examples / Related Tools
prepend: false   # true = insert before the tool's own description, false = after
---
```

## Mode: Tool Approval

```yaml
---
description: Require approval for sensitive operations
enabled: true
id: approval_<unique_id>
name: <Approval Policy Name>
priority: 100   # highest priority recommended
triggers:
  tool_match: [sensitive_tool_1]
  target: tools
type: tool_approval
required_tools: [sensitive_tool_1]     # or required_apps: [app_name]
approval_message: |
  Explain why approval is required and what will happen.
show_code_preview: true
auto_approve_after: null   # null = never auto-approve (recommended); or seconds e.g. 30/60/300
---
```

## Mode: Output Formatter

```yaml
---
description: Format output in a specific structure
enabled: true
id: formatter_<unique_id>
name: <Formatter Name>
priority: 50
triggers:
  natural_language: [format keyword 1]
  target: agent_response   # must be agent_response for formatters
  threshold: 0.6
type: output_formatter
format_type: json   # json | markdown | table | csv | custom
format_config: |
  {"schema": {"type": "object", "properties": {"field1": {"type": "string"}}, "required": ["field1"]}}
---
```

## Testing

```bash
uv run cuga start competition --local
```

Trigger the policy with matching keywords/intent and confirm the expected block/guidance/approval/format behavior shows up.

## Reference

Full worked templates: `docs/starterkit/.cursor/{intent_guard,playbook,tool_guide,tool_approval,output_formatter}.md` in the cuga-agent repo. Policy data models: `src/cuga/backend/cuga_graph/policy/models.py`. SDK docs: https://docs.cuga.dev/docs/sdk/policies/
