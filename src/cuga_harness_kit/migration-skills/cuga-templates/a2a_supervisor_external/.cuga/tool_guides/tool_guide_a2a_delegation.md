---
name: a2a_delegation_guide
description: "How to delegate tasks to external A2A agents in this supervisor"
type: tool_guide
enabled: true
id: tool_guide_a2a_delegation
priority: 50
target_tools:
  # `delegate_to_<agent_name>` is generated per agent (see supervisor_config.yaml
  # `agents:` list) — CugaSupervisor names each delegation tool
  # `delegate_to_{agent_name}` (cuga/backend/cuga_graph/nodes/cuga_supervisor/nodes/
  # prepare_agents_and_prompt.py). Use "*" to apply this guide to all of them, or list
  # specific names, e.g. ["delegate_to_agent_one", "delegate_to_agent_two"].
  - "*"
triggers:
  keywords:
    # {{PLACEHOLDER: add domain keywords that should route through this guide}}
    - delegate
    - agent
  case_sensitive: false
  operator: or
  target: intent
---

# A2A Delegation Guide

## How delegation works

Every agent in this template is `type: external` — an independently deployed HTTP
service that speaks the A2A protocol. There are no internal `CugaAgent` instances and
no direct tool calls; the supervisor's *only* mechanism for doing work is delegating to
one of these external agents.

For each agent entry in `supervisor_config.yaml`, the supervisor exposes an async
Python function named `delegate_to_<agent_name>` (e.g. `agent_one` → `delegate_to_agent_one`).
Calling it:

1. Sends the task as a single natural-language string to the agent's `/a2a` JSON-RPC
   endpoint (`a2a_protocol.endpoint`) via a `message/send` request.
2. The remote agent runs its own logic (any framework) and returns a plain-text result.
3. The delegation call returns that text as the function's return value — never a raw
   HTTP response, dict, or JSON envelope. Treat it as an opaque string.

## Usage pattern

```python
result_one = await delegate_to_agent_one("Do <capability A> for <input>")
print(result_one)
```

```python
# Chaining: embed the previous agent's full text response in the next task string —
# external agents do not share Python variables with each other or the supervisor.
result_two = await delegate_to_agent_two(
    f"Using this input from agent_one:\n{result_one}\n\nNow do <capability B>."
)
print(result_two)
```

## Important notes

- **Each delegation call must be in its own code block**, isolated from other logic —
  same isolation rule as internal-agent delegation (see the supervisor system prompt).
- **No shared variables across services by default.** `variables=[...]` passing (the
  `variables` kwarg on `delegate_to_...`) only works if `supervisor.pass_variables_a2a`
  is enabled in `cuga/settings.toml`; otherwise omit it and embed data as text.
- **Failure signal:** a remote agent's task ending in a failed/errored A2A `state` does
  NOT raise — `create_agent_delegation_func` (cuga/backend/cuga_graph/nodes/cuga_supervisor/
  delegation.py) reads only `result["result"]` (the text) from `delegate_task_via_a2a_sdk`
  and silently discards `result["status"]`. A failed remote task still returns as a normal
  string — possibly empty, if the remote agent didn't put any text in its status message.
  Only transport-level errors (connection refused, timeout, malformed response) raise a
  real exception. So: don't rely on try/except to detect a remote agent failure — inspect
  the returned text itself (e.g. an empty or error-shaped string) and handle it explicitly.
- **Timeouts:** each agent's `a2a_protocol.timeout` (seconds) bounds how long the
  supervisor waits for that agent's response before giving up.
- {{PLACEHOLDER: add any domain-specific delegation ordering rules, e.g. "always call
  agent_one before agent_two"}}
