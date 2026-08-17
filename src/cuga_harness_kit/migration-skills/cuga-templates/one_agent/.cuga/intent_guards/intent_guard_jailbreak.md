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
    - ignore previous instructions
    - ignore all instructions
    - DAN mode
    - jailbreak
    - bypass restrictions
    - write a poem
    - financial advice
    - legal advice
    - medical advice
    # {{PLACEHOLDER: add domain-specific off-topic keywords}}
  case_sensitive: false
  operator: or
  target: intent
---

# Jailbreak and Off-Topic Request Guard

I am a specialized assistant for {{PLACEHOLDER: describe the domain}}.

I cannot help with requests outside my domain. Please ask me about {{PLACEHOLDER: what the agent CAN help with}}.
