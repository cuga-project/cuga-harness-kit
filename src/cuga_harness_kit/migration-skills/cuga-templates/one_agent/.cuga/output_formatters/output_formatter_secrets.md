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

Before returning any response, scan for and redact:

- API keys and tokens (patterns like `sk-...`, `Bearer ...`, `ghp_...`)
- Passwords and credentials
- Connection strings containing usernames/passwords
- Private keys (BEGIN PRIVATE KEY blocks)
- {{PLACEHOLDER: add domain-specific sensitive patterns}}

Replace redacted content with `[REDACTED]`.
