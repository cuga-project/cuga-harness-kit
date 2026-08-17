---
name: cuga-source-sync
description: Use when adding a new source repo to the migrator, to scout it and generate migration hints before running cuga-migrator. Triggers on requests like "sync source hints for <source>", "scout the source repo", "prepare <source> for migration".
---

# CUGA Source Sync

Scout a source repo and write (or update) a `CLAUDE.md` at its root so the `cuga-migrator`
skill's analyst stage can read it first and go straight to relevant files without wasting context
on large test fixtures or build artifacts. Run this once per source repo, before `cuga-migrator`.

## Arguments

Parse the user's request for `<source-name>`.

Source repo path: `migration_from/<source_name>/`
Output: `migration_from/<source_name>/CLAUDE.md`

<Steps>

<Step title="1. Map the directory structure">

List the top-3-level directory tree under `migration_from/<source_name>/`, excluding `.git`,
`node_modules`, and `__pycache__`. Identify the top-level subfolders and their roles.

</Step>

<Step title="2. Find large and noisy files">

List files by line count, largest first. Flag any file over 300 lines living under a noisy
directory pattern as a skip candidate:

| Pattern | Reason to skip |
|---------|---------------|
| `tests/`, `test/`, `__tests__/` | Unit/integration tests — not agent logic |
| `*/mocks/`, `*/fixtures/`, `*/testmode-data/` | Pre-recorded test fixtures |
| `node_modules/`, `dist/`, `build/`, `.next/` | Vendored dependencies / build output |
| `licenses/`, `LICENSE*`, `non_ibm_license*` | License text — not needed |
| `*.lock`, `uv.lock`, `pnpm-lock.yaml` | Dependency lock files |
| `*.db`, `*.pyc`, `*.pyo` | Binary / compiled artifacts |
| `*.html`, `*.png`, `*.pdf` | Non-source assets |

</Step>

<Step title="3. Read the README">

If `README.md` or `README.rst` exists at the source repo root and is under 300 lines, read it.
Extract: what the system does, its main subfolders/repos and their roles, the runtime flow (how
components talk to each other), how to run it.

If a `CLAUDE.md` already exists at the source root, read it too — you will update it, not
overwrite blindly.

</Step>

<Step title="4. Find key entry points">

Scan for: `main.py`, `server.py`, `app.py`, `entrypoint.py`; `*agent*.py`, `*supervisor*.py`,
`*graph*.py`; `*agent*.yaml`, `*config*.yaml`; `.env.template`, `.env.example`;
`requirements.txt`, `pyproject.toml`, `package.json`; one level of `src/` contents. List these as
"key files to read" in priority order.

</Step>

<Step title="5. Write CLAUDE.md">

Write `migration_from/<source_name>/CLAUDE.md` with this structure. If it already exists, update
it — preserve manually written sections that are still accurate, replace stale ones. Write real
content throughout, no placeholders:

```markdown
# <source-name> — Source System Overview

<2-4 sentence description of what the system does>

## Subfolders / repos

### `<subfolder-1>` — <role>
- **What it is:** <one line>
- **Framework:** <language + framework>
- **Key files:** <entry points>
- **Config:** <config file>
- **Run:** <how to start it>

## Relationship

<How components talk to each other — what calls what, the data flow>

## Files to skip — DO NOT READ

| Path | Reason |
|------|--------|
| `<path>` | <why> |

## Key files to read (in order)

1. `<path>` — <why>

## Migration target

<One sentence on what maps to what in CUGA>
```

</Step>

<Step title="6. Report">

Print a one-paragraph summary: what directories were found, how many files were flagged to skip,
which entry points were identified, and whether the CLAUDE.md was created or updated.

</Step>

</Steps>
