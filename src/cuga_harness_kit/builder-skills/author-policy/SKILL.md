---
name: cuga-author-policy
description: Use when the user wants to govern agent behavior with a cuga policy - block/redirect an intent, add playbook guidance, require tool approval, enhance tool descriptions, or reshape output. Covers SDK/file policies and routes managed config to cuga-managed-server.
---

# Authoring a cuga policy

Choose the execution path before saving a policy:

| Path | How to apply the policy |
|---|---|
| SDK | `await agent.policies.add_*`, or `await agent.policies.load_from_folder(".cuga")` |
| File-based SDK/project | Correct `.cuga/` subfolder; enable `auto_load_policies` or explicitly load the folder |
| Managed server | Save policies in the agent's draft config, test, then publish; see `cuga-managed-server` |

Manager mode disables policy filesystem sync. Writing a markdown file and restarting/re-publishing does not import that file into managed config. Markdown frontmatter is a file-loader contract; managed JSON uses serialized policy models (a list of trigger objects, not the file's trigger mapping).

## Choose the type

| Requirement | Type | File directory |
|---|---|---|
| Block or redirect requests | `intent_guard` | `.cuga/intent_guards/` |
| Give workflow guidance | `playbook` | `.cuga/playbooks/` |
| Require tool approval | `tool_approval` | `.cuga/tool_approvals/` |
| Add tool guidance | `tool_guide` | `.cuga/tool_guides/` |
| Shape responses | `output_formatter` | `.cuga/output_formatters/` |

Playbooks and tool guides inject instructions; verify the actual tool calls and output. An intent guard blocks matching requests; tool approval pauses matching tool execution.

## SDK example

```python
import asyncio
from cuga import CugaAgent

async def main():
    agent = CugaAgent(enable_knowledge=False, auto_load_policies=False, filesystem_sync=False)
    try:
        policy_id = await agent.policies.add_intent_guard(
            name="Block Delete Operations",
            keywords=["delete", "remove", "erase"],
            response="Deletion operations are not permitted for security reasons.",
            priority=100,
        )
        assert policy_id
        result = await agent.invoke("delete all records")
        assert not result.error, result.error
        assert result.answer == "Deletion operations are not permitted for security reasons."
        assert any(d.policy_id == policy_id for d in result.policy_decisions)
    finally:
        await agent.aclose()

asyncio.run(main())
```

For guidance: `await agent.policies.add_playbook(name="Budget Analysis", keywords=["budget"], content="# Budget Analysis\n\n1. Read the budget.\n2. Calculate totals.")`. Higher priority is checked first. Configure the LLM and embedding provider before running; keyword examples avoid semantic matching but policy storage still needs embeddings.

## File templates

Save each entire fenced block, including frontmatter and body, to a `.md` file in the listed directory. Body text supplies playbook instructions, guard responses, tool guidance and formatter config. `triggers.keywords` is literal matching; `triggers.natural_language` is semantic matching with a threshold. Tool guide/approval targets come from `target_tools` / `required_tools`, not `triggers.tool_match`.

### Playbook — `.cuga/playbooks/budget.md`

```markdown
---
id: playbook_budget
name: Budget Analysis Workflow
type: playbook
priority: 50
enabled: true
triggers:
  keywords: [budget]
  target: intent
---
# Budget Analysis Workflow

1. Read the budget.
2. Calculate totals and explain assumptions.
```

### Intent Guard — `.cuga/intent_guards/delete.md`

```markdown
---
id: guard_delete
name: Block Delete Operations
type: intent_guard
priority: 100
enabled: true
triggers:
  keywords: [delete, remove, erase]
  target: intent
response_type: natural_language
allow_override: false
---
Deletion operations are not permitted for security reasons.
```

### Tool Guide — `.cuga/tool_guides/lookup.md`

```markdown
---
id: guide_lookup
name: Order Lookup Guidance
type: tool_guide
target_tools: [lookup_order]
prepend: false
---
Use lookup_order with the exact order_id supplied by the user.
```

### Tool Approval — `.cuga/tool_approvals/delete.md`

```markdown
---
id: approval_delete
name: Approve Deletion
type: tool_approval
required_tools: [delete_record]
show_code_preview: true
auto_approve_after: null
---
This will delete a record. Confirm before continuing.
```

### Output Formatter — `.cuga/output_formatters/summary.md`

```markdown
---
id: formatter_summary
name: JSON Summary
type: output_formatter
triggers:
  always: true
format_type: json_schema
---
{"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
```

The file loader accepts `format_type: markdown`, `json_schema`, or `direct`; the body is `format_config`. Do not use `format_type: json` or put formatter/guide/guard content only in frontmatter.

## Verify before claiming success

For SDK file loading, inspect `loaded = await agent.policies.load_from_folder(".cuga")`; require `loaded["count"]` to match the number of intended files and `loaded["errors"]` to be empty. Confirm `await agent.policies.list()` contains their IDs. Run a positive and a negative trigger example. For approvals, confirm interruption and resume on the same `thread_id` with `action_response` (SDK) or the server's documented approval payload. For formatters, parse/validate the returned JSON, not just the prompt.

For manager, check draft behavior and production behavior separately, including `policy_errors` and `status: partial` in API responses. Publish the full tested config; a successful save alone does not prove a policy loaded.

## Reference

Implementation contracts in cuga-agent: `src/cuga/backend/cuga_graph/policy/folder_loader.py`, `models.py`, `src/cuga/sdk.py`, and `src/cuga/backend/server/manage_routes/`. Inspect `uv run cuga policy --help` for storage-level CLI commands; managed config changes belong in the Manage API/UI.
