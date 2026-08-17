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
    # {{PLACEHOLDER: add tool names or operation keywords}}
    - query
    - fetch
    - retrieve
  case_sensitive: false
  operator: or
  target: intent
---

# {{PLACEHOLDER: Data Tools Guide}}

## Tool Overview

{{PLACEHOLDER: Describe what data source these tools access and what data they return.}}

## Tool Usage

### `{{PLACEHOLDER: tool_name_1}}`

**Purpose**: {{PLACEHOLDER: what this tool does}}
**Parameters**:
- `{{PLACEHOLDER: param1}}` (required): {{PLACEHOLDER: description}}
- `{{PLACEHOLDER: param2}}` (optional): {{PLACEHOLDER: description}}

**Return format**:
```json
{
  "{{PLACEHOLDER: field1}}": "{{PLACEHOLDER: description}}",
  "{{PLACEHOLDER: field2}}": "{{PLACEHOLDER: description}}"
}
```

**Example call**:
```
{{PLACEHOLDER: tool_name_1}}({{PLACEHOLDER: param1}}="{{PLACEHOLDER: example_value}}")
```

## Important Notes

- {{PLACEHOLDER: add any critical usage notes, e.g. "Always call tool_A before tool_B"}}
- {{PLACEHOLDER: add parameter format notes, e.g. "Record IDs must include the prefix"}}
- {{PLACEHOLDER: add error handling notes}}
