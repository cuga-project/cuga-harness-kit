# Builder skills review and validation

Reviewed on 2026-10-08 against CUGA v0.4.0, source commit
`ffd0c4700` in cuga-project/cuga-agent. Harness baseline:
`bcf5b364abfd811ef9a3ae03808fa3cd562cd5be`.

The scaffold/render design is useful, but the original builder instructions were
not reliable enough to follow without checking CUGA's implementation. They mixed
embedded SDK configuration with managed server configuration and included several
examples that would not load or execute correctly.

## Corrected findings

| Finding | Correction |
|---|---|
| Managed server draft/publish path was incomplete | Added `cuga-managed-server`, with full config save, draft testing, publish, production checks, authentication and named-agent routing limits |
| `.cuga/guards`, `guides`, `approvals`, `formatters` were not loader directories | Use `intent_guards`, `tool_guides`, `tool_approvals`, `output_formatters` |
| Guard/guide/formatter content was placed in unsupported frontmatter fields | Put response/guidance/formatter configuration in the markdown body |
| Formatter used unsupported `format_type: json` | Use `json_schema`, with an actual schema in the body |
| Tool targeting examples implied `triggers.tool_match` applied | Use `target_tools` / `required_tools` |
| Manager instructions implied files could be imported by restarting/publishing | Use stored draft policies and publish; manager disables policy filesystem sync |
| `CugaSupervisor.from_yaml` was shown without `await` | Document the async factory |
| `cuga policy` and `cuga knowledge` were said not to exist | Verified both in real CLI help; distinguish storage CLI from managed config |
| `cuga doctor` was described as general setup validation | It diagnoses the GPU stack |
| Tool registry integrations were called build-time | Describe runtime registry startup/reload and managed config |
| Codex rendering demoted headings inside fenced examples | Preserve fenced code/templates; demote surrounding document headings only |
| GET config → full POST could erase redacted credentials | Publish an authoritative full config; use section PATCH for narrow draft edits |
| `/run` example omitted machine authentication | Send `X-Gateway-Token` matching `CUGA_RUN_TOKEN` / `GATEWAY_TOKEN`, or an authenticated chat JWT |

## Reproduce checks

The harness itself does not depend on the large CUGA runtime. Its normal suite
checks scaffold behavior, all four assistant targets, frontmatter, fenced example
preservation and syntax of every documented Python block:

```bash
uv sync --locked
uv run pytest
```

Runtime checks are opt-in and require CUGA v0.4.0 with its normal dependencies,
plus pytest and PyYAML. Run in a CUGA environment, using its Python interpreter.
The harness source path makes this review's content importable without replacing
the installed CUGA package. For a source checkout, add its `src` directory too:

```bash
# Replace these three absolute paths for your checkout/environment.
HARNESS_SRC=/absolute/path/to/cuga-harness-kit/src
CUGA_SRC=/absolute/path/to/cuga-agent/src
CUGA_PYTHON=/absolute/path/to/cuga-agent/.venv/bin/python
CUGA_RUNTIME_TESTS=1 PYTHONPATH="$HARNESS_SRC:$CUGA_SRC" \
  "$CUGA_PYTHON" -m pytest /absolute/path/to/cuga-harness-kit/tests/test_builder_runtime.py -q
```

Opting in is an assertion that CUGA is installed. Missing runtime dependencies
fail the opted-in run; they are not silently skipped. Checks use temporary SQLite
storage and isolated policy folders. They supply deterministic embeddings and a
model test double that raises if called, so they need no API keys or model downloads.
Use a separate test process, as the fixture changes CUGA's process-wide settings.

## Results and scope

| Check | Result | What executed |
|---|---|---|
| Normal harness suite | 29 passed; 5 runtime checks skipped | Existing CLI/migration tests plus builder syntax, targets and rendering regressions |
| Runtime suite, Python 3.12 | 5 passed | Real CUGA loaders, SDK, SQLite, policy matching and HTTP configuration/auth routes |
| Five policy file templates | Passed | Exact shipped markdown templates loaded and persisted; response/body fields checked |
| SDK tool and guard | Passed | Shipped addition tool returned `8`; exact documented SDK guard coroutine blocked `delete all records`; nonmatching request did not match |
| Managed config and policy isolation | Passed | Real HTTP draft saves, version 1/2 publishes, draft/published policy storage isolation, required agent name |
| Managed credential preservation | Passed | GET redacted the key; narrow agent PATCH preserved it; authoritative publish retained the stored draft key |
| Run authentication | Passed | Missing/wrong gateway token rejected; configured token accepted by `/run/agents` |
| Runtime skill | Passed | Exact SKILL.md template discovered and loaded through CUGA's SkillRegistry |
| CLI | Passed | Real `cuga --help` advertised `policy` and `knowledge` |
| Package | Passed | Source distribution and wheel built; wheel-installed CLI scaffolded all four assistant targets |

These results do **not** establish live LLM reasoning, multi-agent routing,
OpenAPI/MCP connectivity, approval/resume behavior, model-generated formatter
compliance, RAG ingestion/retrieval/citations, or a complete launched server/UI run.
No model credentials or external services were available for those checks.
The managed HTTP example's live draft/production queries need those prerequisites;
the runtime suite tests configuration, policy application and authentication,
not that entire model-backed script. Require the skill's actual behavioral checks
in the intended deployment before claiming those integrations work.

The runtime run emitted upstream Starlette/httpx and `datetime.utcnow()`
deprecation warnings; all assertions passed.
