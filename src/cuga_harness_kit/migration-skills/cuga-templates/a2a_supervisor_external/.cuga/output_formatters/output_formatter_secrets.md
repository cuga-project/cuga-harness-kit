---
name: secrets_scanner
description: Redact sensitive credentials and tokens from agent outputs
type: output_formatter
enabled: true
id: output_formatter_secrets
priority: 90
triggers:
  keywords:
    - password
    - token
    - secret
    - api_key
    - credential
  case_sensitive: false
  operator: or
  target: agent_response
---

# Secrets Scanner

Before returning any response — including results relayed verbatim from external A2A
agents — scan for and redact:

- API keys and tokens (patterns like `sk-...`, `Bearer ...`, `ghp_...`)
- Passwords and credentials
- Connection strings containing usernames/passwords
- Private keys (BEGIN PRIVATE KEY blocks)
- {{PLACEHOLDER: add domain-specific sensitive patterns}}

Replace redacted content with `[REDACTED]`. This check applies to the supervisor's
final synthesized answer, even when the sensitive content originated in an external
agent's response rather than the supervisor's own output.
