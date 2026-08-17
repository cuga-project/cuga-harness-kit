---
name: data_tools_guide
description: "{{PLACEHOLDER: describe what data tools this guide covers}}"
type: tool_guide
enabled: true
id: tool_guide_data_tools
priority: 50
target_tools:
  - "*"  # {{PLACEHOLDER: replace with specific tool names, e.g. ["fetch_record", "search_records"], or keep ["*"] to apply to all tools}}
triggers:
  keywords:
    - query
    - fetch
    - retrieve
    # {{PLACEHOLDER: add tool-specific keywords}}
  case_sensitive: false
  operator: or
  target: intent
---

# {{PLACEHOLDER: Data Tools Guide}}

## Tool Usage

### `{{PLACEHOLDER: tool_name}}`

**Purpose**: {{PLACEHOLDER: what this tool does}}
**Key parameters**:
- `{{PLACEHOLDER: param}}` (required): {{PLACEHOLDER: description and format}}

**Return format**: `result[1]` contains the actual data (MCP tools return a tuple).

## Important Notes

- {{PLACEHOLDER: add critical usage notes}}
- {{PLACEHOLDER: add parameter format requirements}}
