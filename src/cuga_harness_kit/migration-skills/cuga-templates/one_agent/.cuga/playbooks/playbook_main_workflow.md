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

{{PLACEHOLDER: Write step-by-step instructions for the agent. Be specific about:
1. What information to extract from the user request
2. Which tools to call and in what order
3. What format the output should be in
4. How to handle missing data or errors}}

### Step 1 — Extract request details
- Extract: {{PLACEHOLDER: what to extract, e.g. "record ID", "date range", "section type"}}
- If not provided: {{PLACEHOLDER: what to do if required info is missing}}

### Step 2 — Fetch data
- Call `{{PLACEHOLDER: tool_name}}` with the extracted identifiers
- {{PLACEHOLDER: describe any chained tool calls and their ordering}}

### Step 3 — Produce output
- {{PLACEHOLDER: describe how to compose the final response from tool results}}
- Output format: {{PLACEHOLDER: markdown / JSON / plain text}}

## Output Format

{{PLACEHOLDER: Describe the expected output format with an example template}}

## Error Handling

- If data not found: {{PLACEHOLDER: graceful degradation behavior}}
- If tool call fails: {{PLACEHOLDER: retry strategy or fallback}}
