---
name: cuga-migrator
description: Use when the user wants to migrate a source agent system into a CUGA SDK implementation. Triggers on requests like "migrate <source> to CUGA", "convert this agent system to CUGA SDK", "run the CUGA migration pipeline for <source> as <target>".
---

# CUGA Migrator

Natural-language entry point for the migration pipeline — the same pipeline `/migrate` runs, for
users who ask in plain language instead of typing the slash command.

## Parse the request

Extract from the user's message:
- **source_name** — subfolder under `migration_from/`
- **target_name** — subfolder under `migration_to/`
- **stages** (optional) — if the request asks for only specific stage(s) (e.g. "just run the
  analyst stage", "re-run implementer then evaluator"), extract which one(s), in the order asked:
  `analyst`, `implementer`, `test_writer`, `evaluator`, `debugger`.

If source_name or target_name is missing or ambiguous, ask the user for it before proceeding —
don't guess.

## Run the pipeline

Follow `.claude/commands/migrate.md` in full, using the source_name/target_name/stages extracted
above as if they had been passed as `$ARGUMENTS` to `/migrate`. That file is the single source of
truth for the pipeline logic (stages, human review gates, eval-debug loop, state persistence,
stage-only mode) — do not duplicate or reinterpret it here.
