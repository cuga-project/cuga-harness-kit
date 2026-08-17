---
name: cuga-debug-trajectory
description: Use when a cuga agent run misbehaved (wrong tool called, silently blocked, wrong output format) and the user wants to inspect what actually happened.
---

# Debugging a cuga agent run

## Trajectory viewer

Every run is logged to a trajectory data directory (`<cuga log dir>/trajectory_data`). Inspect it visually:

```bash
cuga viz
```

Launches a web dashboard for browsing execution trajectories: what the reasoning engine decided at each step, which tools it called with what arguments, and what came back. Start here before reading raw logs — it's usually faster to spot the wrong branch/tool call visually than to grep JSON.

## Environment sanity check

```bash
cuga doctor
```

Run this first if the agent won't even start, or behaves inconsistently across environments — it validates the environment/dependency setup.

## `cuga status`

```bash
cuga status <service|all>
```

Confirms whether the service you expect to be running actually is, before chasing a bug that's really just "nothing is listening on that port."

## Common failure patterns

- **Tool "not found" or never called** — check the tool actually got passed to `CugaAgent(tools=[...])`, or (for OpenAPI/MCP tools) that the registry service (`cuga start registry`, or the registry bundled in a `demo_*`/`manager` service) picked up your `mcp_servers.yaml` change — those are build-time, not hot-reloaded.
- **Request silently redirected/blocked with no obvious reason** — an `intent_guard` policy may be matching. Check `.cuga/guards/` (or policies added via `agent.policies.add_intent_guard`) for a guard whose `triggers`/`intent_examples` overlap the query, and check `priority` — guards default to high priority (90-100) and are checked before other policies. See `cuga-author-policy`.
- **Response in the wrong shape** — an `output_formatter` policy may be firing (or not firing when expected) based on its `triggers.natural_language` keywords and `threshold`. Lower/raise the threshold or adjust keywords.
- **Tool paused waiting on nothing** — a `tool_approval` policy is likely gating that tool; check `.cuga/approvals/` for `required_tools`/`required_apps` matches and `auto_approve_after`.
- **`thread_id` confusion** — state (conversation history, session-scoped knowledge) is isolated per `thread_id`. If a run seems to have "forgotten" something from a previous call, confirm the same `thread_id` was passed both times.
- **Multi-agent: wrong sub-agent picked** — the `CugaSupervisor` routes based on each sub-agent's `.description`. Vague or overlapping descriptions between sub-agents cause misrouting — make them distinct and specific.

## Policy-level test coverage

If you're debugging policy interaction bugs specifically, the policy engine's own integration tests are a good reference for expected behavior: `src/cuga/backend/cuga_graph/policy/tests/` in a cuga-agent checkout (covers intent guard blocking/priority resolution, playbook guidance injection, and more).
