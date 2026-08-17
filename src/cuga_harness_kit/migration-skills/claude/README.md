# CUGA Migrator

Converts a source agent system into a CUGA SDK implementation, using Claude Code agents for
analysis, code generation, testing, and debugging.

## Prerequisites

- Claude Code CLI installed and authenticated (`claude` in PATH)
- API keys for the source system and the CUGA runtime (see "Configure credentials" below)

## Setup before running

**1. Add the source repo**

Copy or clone the source agent system into `migration_from/<source-name>/`.

Optionally, run `./source_sync.sh <source-name>` (or ask Claude Code, or `/source_sync
<source-name>`) to auto-generate a `CLAUDE.md` hint file for the analyst — mapping structure,
flagging files to skip, listing entry points.

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
| `.env` | launch scripts | `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` |
| `migration_from/.env` | analyst, test_writer | source system API keys |
| `migration_to/.env` | evaluator | CUGA runtime credentials |

None of these are generated for you — copy `.env.example` to `.env` and fill in the other two.

## Running the migration

```bash
./migrate.sh <source-name> <target-name> [--stages <stage>[,<stage>...]]
```

Sets credentials, runs preflight checks, and opens Agent View so you can watch each stage work.
Run without arguments for interactive prompts. Inside Claude Code you can also use `/migrate
<source-name> <target-name>`, or just ask in plain language (e.g. *"Migrate `<source-name>` to
CUGA as `<target-name>`"*) — all three run the identical pipeline.

The pipeline pauses twice for your review: after the analyst produces `migration_spec.md`, and
after the implementer generates the code. Then the evaluator scores the result — if below 0.8,
the debugger patches it and the evaluator re-runs, up to 3 cycles.

### Running specific stages

```bash
./migrate.sh <source-name> <target-name> --stages analyst
./migrate.sh <source-name> <target-name> --stages analyst,implementer
```

Runs only the listed stage(s), in order, then stops — no review gates, no eval-debug looping.
Each stage needs its prerequisite already on disk:

| Stage | Needs first |
|---|---|
| `analyst` | the source repo under `migration_from/<source-name>/` |
| `implementer` | `migration_spec.md` (`--stages analyst`) |
| `test_writer` | ground truth `.txt` files |
| `evaluator` | `test_cases.json` and `migration_spec.md` |
| `debugger` | `eval_report.json` (`--stages evaluator`) |

## Directory layout

```
migration_from/<source-name>/   # your source repo (read-only)
migration_to/
  cuga-agent/                   # CUGA SDK (reference + runtime)
  <target-name>/                # generated implementation
  data/ground_truth/            # your test input/output pairs
  data/prediction/               # eval outputs, incl. eval_report.json
cuga-templates/                 # CUGA scaffolds per architecture
.cuga-migrator/                 # pipeline state (auto-generated)
  migration_spec.md             # analyst's design document
  state.json                    # progress tracker, for resuming
  user_request.md                # your intent, if any
```

## Pipeline stages

| Stage | What it does |
|-------|-------------|
| `analyst` | Reads the source + CUGA SDK + templates → writes `migration_spec.md` |
| `implementer` | Reads the spec + templates → writes the CUGA implementation |
| `test_writer` | Reads ground truth → writes `test_cases.json` |
| `evaluator` | Runs the implementation, scores it → writes `eval_report.json` |
| `debugger` | Reads failures → patches the implementation |

## Resuming

If a migration was interrupted, run `./migrate.sh <source-name> <target-name>` again — it reads
`.cuga-migrator/state.json` and skips completed stages.

## Read-only directories

Never modified during a migration: `migration_to/cuga-agent/` (SDK runtime), `migration_from/`
(source reference), `migration_to/data/ground_truth/` (evaluation source of truth).
