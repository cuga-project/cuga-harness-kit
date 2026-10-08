# cuga-harness-kit

Skills that teach Claude Code, Cursor, Codex, and Bob how to install, launch, and build with [cuga](https://github.com/cuga-project/cuga-agent) — the open-source generalist agent framework.

## Assistant quickstart

Paste this into Claude Code, Cursor, Codex, or Bob from the project folder you want to set up:

```text
Run `uv tool install --upgrade git+https://github.com/cuga-project/cuga-harness-kit.git`, then `cuga-harness-kit init` in this folder. Read and follow the `using-cuga` skill first: verify my existing LLM configuration or help me configure it, then ask what I want to build and help me choose SDK or managed-server mode before implementation. Reuse choices and successful checks I have already provided.
```

This prompt installs repository main to include the latest builder skills. Published releases can also be installed through PyPI using the commands below.

The assistant will install this kit, scaffold the cuga guidance files, then follow `using-cuga`:

1. Inspect the existing project and reuse any established provider, execution mode, and successful checks.
2. Configure your LLM provider and verify a model request. Install CUGA for a local SDK app or local server when needed; use existing server-side configuration for a remote managed-server client.
3. Explain what you want to build and choose SDK embedding (usually your own app/UI) or a managed CUGA server (Manage UI, draft/publish config, HTTP clients). A custom UI can use either path.
4. Ask *"help me build a cuga tool"* or *"how do I add a policy"* when you're ready to build.

## Manual install

No git clone, no marketplace install:

```bash
uv tool install cuga-harness-kit
(if update: uv pip install -e . --reinstall-package cuga-harness-kit)
cuga-harness-kit init
```

If you're installing inside an already-active virtualenv instead of as a CLI tool, use `uv pip install cuga-harness-kit`.

Run `init` from an empty new project you're starting from scratch, or from inside an existing cuga checkout — either way it writes the same skill set into the current directory:

- `.claude/skills/<name>/SKILL.md` — auto-discovered by Claude Code.
- `.cursor/rules/cuga-<name>.mdc` — auto-discovered by Cursor.
- `AGENTS.md` — read by Codex. Re-running `init` only touches the managed block, so it won't clobber the rest of the file.
- `.bob/skills/<name>/SKILL.md` — auto-discovered by IBM Bob.
- `docs/cuga-env-api-keys.md` — local reference for `.env` API-key setup.

## What's included

| Skill | Teaches |
|---|---|
| `using-cuga` | New-build entry point: verify LLM configuration, understand the goal, choose SDK or managed server with the user. |
| `getting-started` | Routes focused requests to the appropriate builder skill. |
| `install-and-launch` | `uv init`, `uv add cuga`, `.env` API keys, `uv run cuga start <mode>`. |
| `build-agent` | Embedded single-agent `CugaAgent` SDK basics. |
| `build-supervisor` | SDK and managed multi-agent teams, specialist ID references, delegation, draft/publish checks and supervisor demos. |
| `managed-server` | Manage UI/HTTP draft → test → publish config; production invocation. |
| `build-cuga-skill` | Authoring cuga's own **runtime** skills — not the same as the IDE-assistant skills in this repo. |
| `build-tool` | Registering a LangChain / OpenAPI / MCP tool. |
| `author-policy` | Intent guards, playbooks, tool approval/guides, output formatters. |
| `knowledge-rag` | Document ingestion/search. |
| `debug-trajectory` | `cuga viz`, `cuga doctor`, common failure patterns. |

Each is authored once as a `SKILL.md` under `src/cuga_harness_kit/builder-skills/`, then rendered into the Cursor/Codex shapes (or used verbatim for Claude/Bob) at `init` time.

## CLI

```bash
cuga-harness-kit init [--targets claude,cursor,codex,bob] [--force] [--dry-run]
cuga-harness-kit update   # alias for `init --force`
```

- `--targets` — comma-separated subset of `claude`, `cursor`, `codex`, `bob` (default: all four).
- `--force` — overwrite scaffolded files that already exist and differ (default: skip and report).
- `--dry-run` — print what would be written without touching disk.

## Migration pipeline (optional, claude/bob only)

Besides the guidance skills above, this kit can also scaffold **cuga-migrator** — a separate tool
that converts an *existing* agent system into a cuga SDK implementation, via a 5-stage pipeline
(analyst → implementer → test_writer → evaluator → debugger). It's opt-in and exclusive: it
replaces the guidance skills for that run rather than adding to them.

```bash
cuga-harness-kit init --targets claude --migration   # or --targets bob
```

This scaffolds the migration skills/agents, launch scripts, `cuga-templates/`, and
`migration_from/`/`migration_to/`, then clones the [cuga SDK](https://github.com/cuga-project/cuga-agent)
for the pipeline to reference. Once scaffolded, three more subcommands become available, grouped
under `migrate`:

```bash
cuga-harness-kit migrate source_sync <source-name>
cuga-harness-kit migrate cuga_sync
cuga-harness-kit migrate run <source-name> <target-name>
```

You can also just ask Claude Code / Bob directly, in natural language. See the scaffolded kit's
own `README.md` for the full walkthrough. Useful flags: `--skip-sdk` (don't clone the SDK),
`--cuga-ref <branch-or-tag>` (pin a version).

## Updating

New releases of `cuga-harness-kit` ship improved skill content. To pick it up in a project that already ran `init`:

```bash
uv tool upgrade cuga-harness-kit
cuga-harness-kit update
```

`update` overwrites scaffolded files unconditionally — if you hand-edited one to customize it, `update` will clobber that edit (there's no diff/merge, except for `AGENTS.md`'s managed block). Copy customizations out first if you want to keep them.

## cuga project setup

When the generated skills help you install cuga in an app, they default to a `uv` project so dependencies are captured in `pyproject.toml`:

```bash
uv init my-cuga-app
cd my-cuga-app
uv add cuga
```

The SDK configures an agent in your Python process. The managed server reads per-agent draft and published versions from its config store. SDK tools/policies and `.cuga/` files do not automatically update managed config; use the managed-server skill for that workflow.

For API keys and provider settings, see [`docs/env-api-keys.md`](docs/env-api-keys.md).

## Development

```bash
uv sync
uv run pytest
```

For the runtime-backed builder checks and their coverage limits, see [builder validation](docs/builder-validation.md).
