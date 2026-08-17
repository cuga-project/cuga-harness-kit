---
name: my_skill  # {{PLACEHOLDER: replace with skill name, matching the directory name}}
description: >
  {{PLACEHOLDER: one-line description of when to use this skill.
  Format: "Use when the user asks to <action> with <subject>."
  This description is shown in the agent's skill list — be specific enough to
  distinguish this skill from others.}}
---

# {{PLACEHOLDER: Skill Display Name}}

## When to Use

Use this skill when the user asks to:
- {{PLACEHOLDER: specific trigger phrase 1}}
- {{PLACEHOLDER: specific trigger phrase 2}}

Do NOT use for: {{PLACEHOLDER: list cases where a DIFFERENT skill should be used instead}}.

## Workflow

### Step 1 — Extract request details
- Extract: {{PLACEHOLDER: what to extract from the user query}}
- If missing: {{PLACEHOLDER: what to ask or assume}}

### Step 2 — Fetch data (if applicable)

{{PLACEHOLDER: describe which tools to call and in what order.
Include a table like:

| Input | Tools to call (in order) |
|-------|--------------------------|
| case A | tool_1 → tool_2 |
| case B | tool_1 → tool_3 |

}}

### Step 3 — Produce output

{{PLACEHOLDER: describe the output format and any templates to follow}}

## Output Format

{{PLACEHOLDER: show an example output template}}

## Error Handling

- If data not found: {{PLACEHOLDER: graceful degradation behavior}}
- If tool call fails: {{PLACEHOLDER: retry strategy or fallback}}
