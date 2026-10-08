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
| `/run` example omitted machine authentication and the route feature gate | Set `CUGA_EVENTS_ENABLED=true` before server launch, configure a token, verify `/openapi.json`, and authenticate requests |
| Managed tool descriptions were omitted | Supply nonempty descriptions; otherwise real agent prompt construction crashes after successful discovery |
| Managed OpenAPI `include` example assumed operation IDs also matched callable names | Omit `include` for affected v0.4.0 entries; registry and agent apply different filters to the same values |
| Always-triggered formatter loaded but never matched | Use an explicit keyword trigger and test both matching and nonmatching requests |
| JSON schema lacked the title required by structured output initialization | Add `title: SummaryResponse` and parse the returned JSON |
| SDK knowledge flag was described as overriding all settings | Also enable the global engine and intended scopes; direct SDK knowledge operations enforce those settings |
| Automatic SDK retrieval fails before search | Record `Unexpected argument(s) for knowledge_search_knowledge: thread_id`; remove the unverified automatic-answer claim and document explicit retrieval |
| New builders needed provider readiness and execution-mode guidance | Added `using-cuga`: reuse existing configuration, verify an actual model request, understand the application goal, and choose SDK or managed server with the user |

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
storage and isolated policy folders. They supply deterministic embeddings and scripted chat responses for SDK
graph checks; storage/guard checks reject model calls. No API keys or model
downloads are needed.
Use a separate test process, as the fixture changes CUGA's process-wide settings.

## Reproduce full local execution checks

The network suite starts its own CUGA server, registry, MCP HTTP and stdio
services, and an OpenAI-compatible HTTP fixture on unused loopback ports. It
uses temporary databases, an empty config environment, synthetic documents,
and placeholder credentials. Its environment whitelist excludes operator
provider/proxy/registry/config overrides. It shuts down the processes it starts.
It does not target an existing managed server.

```bash
CUGA_NETWORK_TESTS=1 PYTHONPATH="$HARNESS_SRC:$CUGA_SRC" \
  "$CUGA_PYTHON" -m pytest /absolute/path/to/cuga-harness-kit/tests/test_builder_network.py -q

# Run the complete suite, including both opt-in suites:
CUGA_RUNTIME_TESTS=1 CUGA_NETWORK_TESTS=1 PYTHONPATH="$HARNESS_SRC:$CUGA_SRC" \
  "$CUGA_PYTHON" -m pytest /absolute/path/to/cuga-harness-kit/tests -q
```

The model and embedding HTTP responses are deliberately scripted, including
which tool/delegate to call. The actual CUGA graph, argument handling, tool
executors, network transports, config database, policy engine, knowledge engine,
and storage execute normally. These are orchestration/protocol tests, not an
assessment of a real model's reasoning, routing choices, embedding quality, or
retrieval relevance. Fixtures are in `tests/fixtures/`.

## Results and scope

Follow-up execution checks on 2026-10-08 exposed additional defects and runtime
limitations that configuration-only tests did not catch. This report supersedes
the original 34-test validation scope.

| Check | Result | What executed |
|---|---|---|
| Complete opted-in suite | 48 passed; 1 expected failure | All normal, runtime and network checks together, including onboarding and SDK/managed supervisor checks |
| Default harness suite | 31 passed; 18 opt-in checks skipped | Scaffold/migration checks, all 11 skills across four assistant targets, syntax and fenced rendering |
| Runtime suite, Python 3.12 | 11 passed | Real loaders, SDK graphs, SQLite, policies, Manage routes and authentication |
| Network suite | 6 passed; 1 expected failure | Launched actual server and registry, exact managed script, model readiness, three tool transports, knowledge storage and the classified SDK RAG failure |
| `using-cuga` LLM check | Passed with local HTTP fixture | Exact shipped model-factory example completed a real OpenAI-compatible request; a bad endpoint returned 404 and failed without claiming readiness or printing the test key |
| `using-cuga` routing | Independent simulation passed | Existing FastAPI/React SDK app, React client for an existing named server, and first-time sales assistant; preserve prior checks and avoid unnecessary local SDK/admin setup |
| SDK single-agent example | Passed | Entire shipped coroutine; arithmetic tool actually called with `a=5`, `b=3`, returned `8` |
| SDK supervisor example | Passed | Entire moved `build-supervisor` coroutine; CRM output passed to email, with recipient and customer-record arguments checked |
| Managed supervisor | Passed with launched server/MCP fixtures | Exact config shapes and invocation example; named creation/routing, specialist publication, five CRM-to-email executions, draft instruction isolation, independent specialist publication and disabled-registry rejection |
| Named draft tool catalog | Confirmed limitation | A newly created named draft answered without executing its draft-only CRM tool; published definitions plus a scoped registry reload provisioned the catalog after the initial draft query cached it empty; catalog checks after named tool publication are required |
| Supervisor CLI entry points | Help verified | Installed CLI advertises `demo_supervisor` and `--seed-supervisor-demo`; no demo services launched by this check |
| Supervisor demo seed | Passed | Real seed function stored CRM/email/filesystem specialists and supervisor as drafts and published versions; internal references and filesystem flag checked |
| Five policy templates | Passed | Exact file blocks loaded and persisted, with body fields checked |
| Intent guard | Passed | Exact shipped guard coroutine blocked matching input; nonmatching input did not match |
| Tool approval/resume | Passed | Shipped approval file interrupted; accept on the same thread executed once; deny executed zero times |
| Output formatter | Passed after correction | Exact shipped formatter file matched `summary`, returned parseable JSON, and skipped nonmatching input |
| Managed local JSON workflow | Passed after route-gate correction | Exact shipped HTTP script saved draft, invoked draft, published a version, verified config and invoked production |
| Managed policies and credentials | Passed | Draft/published policy isolation, version changes, redacted GET and credential-preserving section PATCH |
| MCP HTTP and stdio | Passed | Documented config shapes, discovery, real fixture calls and audited transport counts in draft and production; compatible original-name `include` selection after publish |
| OpenAPI | Passed without `include` | Discovered callable name used by actual agent in draft and production; endpoint counters prove two HTTP calls |
| Manage UI | Manual pass | Opened dashboard/config UI, saved an agent name, published v3, and received a completed draft chat greeting from the HTTP fixture |
| Knowledge ingestion/retrieval/isolation | Passed for `.txt` | Real engine indexed a synthetic report, retrieved the revenue passage and isolated two session document lists |
| Automatic SDK RAG and citations | Confirmed failure | Injected search rejected `thread_id` before retrieval; no sources returned; narrow strict expected-failure regression retained |
| Runtime skill | Passed | Exact runtime skill template discovered and loaded through SkillRegistry |
| CLI/package | Initial review passed | Real CLI help, source/wheel builds and installed scaffolds for all four targets |

These checks used local model fixtures rather than a hosted LLM. Real LLM reasoning and routing
quality, hosted embedding-provider compatibility/quality, PDF/DOCX/image parsing,
OCR, managed knowledge upload/RAG, external A2A/ACP delegation, authenticated
Manage/JWT flows, deployment export/import, and full CLI-launch-to-chat supervisor
demos remain unvalidated. The supervisor demo seed was executed against isolated
storage; it does not establish that every bundled demo tool or model works. The UI check
used the same scripted HTTP provider. SDK automatic RAG is a confirmed runtime
failure, not merely an unavailable-credentials check. Do not report all paths as
working, or citations as verified, on this reviewed source version.

A successful `/run` response can contain an answer after a failed tool attempt.
The network tests require response markers AND service-side counters, and the
RAG test inspects tool errors and sources. Checking HTTP 200, `ok`, or
`result.error` alone would have missed these failures.

The runtime suite emitted upstream Starlette/httpx and `datetime.utcnow()`
deprecation warnings; passing assertions were unaffected.
