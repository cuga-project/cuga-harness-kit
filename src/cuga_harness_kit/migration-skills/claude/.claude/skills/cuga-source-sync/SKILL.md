---
name: cuga-source-sync
description: Use when adding a new source repo to the migrator, to scout it and generate migration hints before running cuga-migrator. Triggers on requests like "sync source hints for <source>", "scout the source repo", "prepare <source> for migration".
---

# CUGA Source Sync

Natural-language entry point for source scouting — the same work `/source_sync` does, for users
who ask in plain language instead of typing the slash command.

## Parse the request

Extract **source_name** (subfolder under `migration_from/`) from the user's message. If it's
missing or ambiguous, ask before proceeding — don't guess.

## Run it

Follow `.claude/commands/source_sync.md` in full, using the source_name extracted above as if it
had been passed as `$ARGUMENTS` to `/source_sync`. That file is the single source of truth for
the scouting logic — do not duplicate or reinterpret it here.
