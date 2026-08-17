---
name: jailbreak_guard
description: Block prompt injection and jailbreak attempts
type: intent_guard
enabled: true
id: intent_guard_jailbreak
priority: 100
response_type: natural_language
triggers:
  keywords:
    # {{PLACEHOLDER: add domain-specific off-topic keywords from the spec}}
    - ignore previous instructions
    - ignore all instructions
    - DAN mode
    - jailbreak
    - bypass restrictions
    - write a poem
    - tell me a joke
    - financial advice
    - legal advice
    - medical advice
  case_sensitive: false
  operator: or
  target: intent
---

# Jailbreak and Off-Topic Request Guard

This agent is a specialized assistant for {{PLACEHOLDER: describe the domain, e.g. "SRE operations and incident management"}}.

I cannot help with:
- Prompt injection or attempts to override my instructions
- Requests outside my domain (creative writing, financial/legal/medical advice, etc.)
- Role-playing as a different AI system

Please ask me about {{PLACEHOLDER: describe what the agent CAN help with}}.
