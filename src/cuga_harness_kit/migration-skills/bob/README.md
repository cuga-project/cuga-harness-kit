# CUGA Migrator (Bob)

Converts a source agent system into a CUGA SDK implementation, using Bob skills for analysis,
code generation, testing, and debugging. Same pipeline as the Claude Code version, ported to
Bob's skill-based model (Bob has no named sub-agents, slash commands, or hooks — the whole
pipeline runs as three Bob skills instead).

## Prerequisites

- Bob IDE, with this folder open as the active project
- API keys for the source system and the CUGA runtime (see "Configure credentials" below)
- **This folder trusted by Bob.** Run `bob` here interactively once and choose "Trust folder"
  before using `--yolo` or the launch scripts below — an untrusted folder silently runs in a
  read-only safe mode with no error. Also check Bob Settings → Auto-Approve → **Skills** is on.

## Setup before running

**1. Add the source repo**

Copy or clone the source agent system into `migration_from/<source-name>/`.

Optionally, ask Bob *"Sync source hints for `<source-name>`"* (or run `./source_sync.sh
<source-name>`) to auto-generate a `CLAUDE.md` hint file for the analyst.

**2. (Optional) Add a user request**

`.cuga-migrator/user_request.md` already exists — edit it if you want to steer the migration
(a specific architecture, naming conventions, reuse preferences, etc.). It's read at the start of
every run, even if you leave it empty.

```
# User Request
Use the A2A approach to orchestrate the existing agents as external services.
```

**3. Add ground truth**

Place `.txt` trace files in `migration_to/data/ground_truth/`, each with a `USER INPUT` and a
`FINAL OUTPUT` section. If you have none yet, the pipeline pauses and asks for them before testing.

**4. Configure credentials**

Three `.env` files, all gitignored:

| File | Used by | Contents |
|------|---------|-------------------|
| `.env` | (optional) tracing | see `.env.example` |
| `migration_from/.env` | source_sync, test_writer | source system API keys |
| `migration_to/.env` | evaluator | CUGA runtime credentials |

Bob manages its own model credentials at the IDE level, so there's no `ANTHROPIC_AUTH_TOKEN` here
unlike the Claude Code version. None of these files are generated for you — copy `.env.example` to
`.env` and fill in the other two.

## Running the migration

Ask Bob something like *"Migrate `<source-name>` to CUGA as `<target-name>`"* and it will activate
the `cuga-migrator` skill. There's no `/migrate` command the way Claude Code has one — phrase the
request naturally.

Or run `./migrate.sh <source-name> <target-name> [--stages <stage>[,<stage>...]]`. This always
opens an **interactive** `bob` session (Bob can't pause mid-run for review gates otherwise) and
copies your request to the clipboard for you to paste as the first message. If Bob opens and seems
to just sit there, that's not a hang — paste and press Enter.

The pipeline pauses twice for your review: after the analyst produces `migration_spec.md`, and
after the implementer generates the code. Then the evaluator scores the result — if below 0.8,
the debugger patches it and the evaluator re-runs, up to 3 cycles.

`source_sync.sh` and `cuga_sync.sh` run non-interactively — no review gates. Set
`BOBSHELL_API_KEY` in `.env` before running any launch script.

### Running specific stages

```bash
./migrate.sh <source-name> <target-name> --stages analyst
./migrate.sh <source-name> <target-name> --stages analyst,implementer
```

Or phrase it naturally, e.g. *"just re-run the analyst then implementer stages for
`<target-name>`"*. Runs only the listed stage(s), in order, then stops — no review gates, no
eval-debug looping. Each stage needs its prerequisite already on disk:

| Stage | Needs first |
|---|---|
| `analyst` | the source repo under `migration_from/<source-name>/` |
| `implementer` | `migration_spec.md` (the analyst stage) |
| `test_writer` | ground truth `.txt` files |
| `evaluator` | `test_cases.json` and `migration_spec.md` |
| `debugger` | `eval_report.json` (the evaluator stage) |

## Directory layout

```
migration_from/<source-name>/   # your source repo (read-only)
migration_to/
  cuga-agent/                   # CUGA SDK (reference + runtime) — clone it here yourself
  <target-name>/                # generated implementation
  data/ground_truth/            # your test input/output pairs
  data/prediction/               # eval outputs, incl. eval_report.json
cuga-templates/                 # CUGA scaffolds per architecture
.cuga-migrator/                 # pipeline state (auto-generated)
  migration_spec.md             # analyst's design document
  state.json                    # progress tracker, for resuming
  user_request.md                # your intent, if any
.bob/skills/
  cuga-migrator/                # the 5-stage pipeline
  cuga-source-sync/              # standalone: scout a new source repo
  cuga-template-sync/            # standalone: sync templates with the current SDK
migrate.sh / source_sync.sh / cuga_sync.sh   # launch scripts, one per skill above
```

## Pipeline stages

| Stage | What it does |
|-------|-------------|
| `analyst` | Reads the source + CUGA SDK + templates → writes `migration_spec.md` |
| `implementer` | Reads the spec + templates → writes the CUGA implementation |
| `test_writer` | Reads ground truth → writes `test_cases.json` |
| `evaluator` | Runs the implementation, scores it → writes `eval_report.json` |
| `debugger` | Reads failures → patches the implementation |

All 5 stages run inside the `cuga-migrator` skill, one subagent at a time (Bob doesn't run
subagents concurrently).

## Resuming

If a migration was interrupted, just ask again — the orchestrator reads
`.cuga-migrator/state.json` and skips completed stages.

## Read-only directories

Never modified during a migration: `migration_to/cuga-agent/` (SDK runtime), `migration_from/`
(source reference), `migration_to/data/ground_truth/` (evaluation source of truth).
