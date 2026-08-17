---
name: main_workflow_guide
description: "{{PLACEHOLDER: one-line description of the main workflow this playbook covers}}"
type: playbook
enabled: true
id: playbook_main_workflow
priority: 50
triggers:
  keywords:
    # {{PLACEHOLDER: add keywords that trigger this workflow, e.g. "compose", "create", "generate"}}
    - create
    - generate
    - compose
    - draft
  case_sensitive: false
  operator: or
  target: intent
---

# {{PLACEHOLDER: Main Workflow Name}}

## Purpose

{{PLACEHOLDER: Describe what this workflow does and when it applies.}}

## Workflow Steps

{{PLACEHOLDER: Write step-by-step instructions for the supervisor. This template's
agents are ALL external A2A services (no internal CugaAgent sub-agents) — every step
below is a delegation to an external agent, never a direct tool call. Be specific about:
1. What information to extract from the user request
2. Which external A2A agents to delegate to and in what order
3. What format the output should be in
4. How to handle a delegated agent returning an error/failed status}}

### Step 1 — Extract request details
- Extract: {{PLACEHOLDER: what to extract, e.g. "record ID", "date range", "section type"}}
- If not provided: {{PLACEHOLDER: what to do if required info is missing}}

### Step 2 — Delegate to the first external agent
- Delegate to `{{PLACEHOLDER: agent_one name}}` with a natural-language task string
  describing the extracted request details (see `tool_guide_a2a_delegation.md` for the
  exact delegation pattern — send text, receive text).
- Wait for the agent's full text response before proceeding.

### Step 3 — Delegate to the next agent (if needed)
- Delegate to `{{PLACEHOLDER: agent_two name}}`, embedding the previous agent's response
  directly in the task string (A2A agents only receive plain text — no shared variables
  across services unless `pass_variables_a2a` is enabled).
- Specify the output format: {{PLACEHOLDER: markdown / JSON / plain text}}

## Output Format

{{PLACEHOLDER: Describe the expected output format with an example template}}

## Error Handling

- If an external agent is unreachable or times out: {{PLACEHOLDER: how to handle — retry once, report the failure, or fall back to another agent}}
- If an external agent's response has `status: failed`: {{PLACEHOLDER: how to surface this to the user}}
