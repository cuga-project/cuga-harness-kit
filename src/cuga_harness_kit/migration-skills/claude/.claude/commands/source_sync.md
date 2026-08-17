---
description: Scout a source repo and write a CLAUDE.md that guides the analyst — maps structure, flags large files to skip, and lists key entry points in read order. Usage: /source_sync <source-name>
allowed-tools: Read, Write, Edit, Bash
---

You are the **Source Sync Agent**. Your job is to scout the source repo and write (or update) a `CLAUDE.md` so that the analyst can read it first and go straight to the relevant files without wasting context on large test fixtures or build artifacts.

## Arguments

The user passed: `$ARGUMENTS`

Parse this as: `<source-name>`

Source repo path: `migration_from/<source_name>/`
Output: `migration_from/<source_name>/CLAUDE.md`

## Step 1 — Map the directory structure

Run a `find` to get the top-3-level directory tree, excluding `.git`, `node_modules`, and `__pycache__`:

```bash
find migration_from/<source_name>/ -maxdepth 3 \
  -not -path '*/.git/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' \
  | sort
```

From the output, identify the top-level subfolders and their roles.

## Step 2 — Find large and noisy files

Run:

```bash
find migration_from/<source_name>/ -type f \
  -not -path '*/.git/*' \
  | xargs wc -l 2>/dev/null \
  | sort -rn \
  | head -40
```

Flag any file over 300 lines that lives under a noisy directory pattern as a skip candidate. Noisy patterns:

| Pattern | Reason to skip |
|---------|---------------|
| `tests/`, `test/`, `__tests__/` | Unit/integration tests — not agent logic |
| `*/mocks/`, `*/fixtures/`, `*/testmode-data/` | Pre-recorded test fixtures |
| `node_modules/`, `dist/`, `build/`, `.next/` | Vendored dependencies / build output |
| `licenses/`, `LICENSE*`, `non_ibm_license*` | License text — not needed |
| `*.lock`, `uv.lock`, `pnpm-lock.yaml` | Dependency lock files |
| `*.db`, `*.pyc`, `*.pyo` | Binary / compiled artifacts |
| `*.html`, `*.png`, `*.pdf` | Non-source assets |

## Step 3 — Read the README

If a `README.md` or `README.rst` exists at the source repo root and is under 300 lines, read it. Extract:
- What the system does
- Its main subfolders / repos and their roles
- The runtime flow (how components talk to each other)
- How to run it

If an existing `CLAUDE.md` already exists, read it too — you will update it rather than overwrite blindly.

## Step 4 — Find key entry points

Scan for files matching these patterns (use `find` with `-name`):

- `main.py`, `server.py`, `app.py`, `entrypoint.py`
- `*agent*.py`, `*supervisor*.py`, `*graph*.py`
- `*agent*.yaml`, `*config*.yaml`
- `.env.template`, `.env.example`
- `requirements.txt`, `pyproject.toml`, `package.json`
- `src/` directory contents (one level deep)

List these as the "key files to read" in priority order.

## Step 5 — Write CLAUDE.md

Write `migration_from/<source_name>/CLAUDE.md` using the structure below. If the file already exists, update it — preserve any manually written sections that are still accurate, replace stale ones.

```markdown
# <source-name> — Source System Overview

<2–4 sentence description of what the system does, inferred from the README or directory structure.>

## Subfolders / repos

### `<subfolder-1>` — <role>
- **What it is:** <one line>
- **Framework:** <language + framework>
- **Key files:** <entry points>
- **Config:** <config file>
- **Run:** <how to start it>

### `<subfolder-2>` — <role>
(same structure)

## Relationship

<Brief description of how the components talk to each other — what calls what, what is the data flow.>

```
<ASCII flow diagram if helpful>
```

## Files to skip — DO NOT READ

<Only list files / directories that are actually present and large enough to matter.>

| Path | Reason |
|------|--------|
| `<path>` | <why — e.g. "pre-recorded mock JSON, 105k lines"> |

## Key files to read (in order)

<List only files that are actually present. Ordered from most important to least.>

1. `<path>` — <why: e.g. "main agent definitions and tool lists">
2. `<path>` — <why>
3. ...

## Migration target

<One sentence on what maps to what in CUGA — e.g. "X maps to supervisor + sub-agents; Y maps to FastMCP MCP servers.">
```

Write real content throughout — no placeholder text. Base everything on what you observed in Steps 1–4.

## Sync report

After writing the CLAUDE.md, print a one-paragraph summary: what directories were found, how many files were flagged to skip, which entry points were identified, and whether the CLAUDE.md was created or updated.
