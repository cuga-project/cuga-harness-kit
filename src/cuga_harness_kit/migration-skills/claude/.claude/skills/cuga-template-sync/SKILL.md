---
name: cuga-template-sync
description: Use when the CUGA SDK (migration_to/cuga-agent/) has been updated and templates need to be checked for drift before the next migration. Triggers on requests like "sync CUGA templates", "check templates against the SDK", "update templates for the new CUGA SDK version".
---

# CUGA Template Sync

Natural-language entry point for template drift-checking — the same work `/cuga_sync` does, for
users who ask in plain language instead of typing the slash command. No arguments needed.

## Run it

Follow `.claude/commands/cuga_sync.md` in full — that file is the single source of truth for the
drift-check logic; do not duplicate or reinterpret it here.
