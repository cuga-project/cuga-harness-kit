---
name: cuga-getting-started
description: Use when the user wants to install, launch, or build something with the cuga agent framework (pip package `cuga`), or asks "how do I use cuga" / "how do I build an agent with cuga" — routes to the right cuga-harness-kit skill instead of guessing.
---

# Getting started with cuga

cuga (`uv add cuga`, [github.com/cuga-project/cuga-agent](https://github.com/cuga-project/cuga-agent)) is an agent orchestration framework: a reasoning engine + pluggable tools (OpenAPI/MCP/LangChain) + a policy system + optional RAG knowledge base + multi-agent supervision, built on LangGraph.

This skill is the entry point. Read the description of the skill that matches what the user is doing before improvising:

| User is trying to... | Use skill |
|---|---|
| Install cuga or start the demo UI | `cuga-install-and-launch` |
| Write Python code that creates/invokes a `CugaAgent` or `CugaSupervisor` | `cuga-build-agent` |
| Author a new **runtime** skill the agent itself can load (`.cuga/skills/<name>/SKILL.md`) | `cuga-build-cuga-skill` |
| Register a Python function, OpenAPI spec, or MCP server as a callable tool | `cuga-build-tool` |
| Add a policy: block an intent, add a playbook, require approval, enhance a tool description, or reshape output | `cuga-author-policy` |
| Ingest/search documents (RAG) | `cuga-knowledge-rag` |
| An agent run misbehaved and you need to inspect why | `cuga-debug-trajectory` |

## Two different meanings of "skill"

Don't conflate these — they are unrelated mechanisms that happen to share the `SKILL.md` filename convention:

1. **This skill** (and its siblings) is an *IDE-assistant* skill — it teaches you, the coding assistant, how to work with cuga.
2. **cuga's own runtime skills** (`.cuga/skills/<name>/SKILL.md`) are loaded by a running `CugaAgent` via a `load_skill` tool, and are what the *agent itself* can call at runtime. See `cuga-build-cuga-skill` when the user wants one of these.

## Ground truth over memory

cuga's CLI and SDK surface can change between versions. If something in these skills looks stale (a flag, a command, a class name), verify against the installed package before trusting the skill text: `python -c "import cuga; print(cuga.__file__)"`, `cuga --help`, or the repo at `src/cuga/` if working inside a checkout.
