---
name: cuga-install-and-launch
description: Use when the user wants to install cuga, start the demo/web UI, or asks what `cuga start` does or which service/mode to run.
---

# Installing and launching cuga

## Install

For a new app project, initialize with `uv` and add `cuga` as a dependency so it is recorded in `pyproject.toml`:

```bash
uv init my-cuga-app
cd my-cuga-app
uv add cuga
```

For an existing project that already has a `pyproject.toml`, run `uv add cuga` from the project root. If the user only wants a quick install inside an already-active virtualenv, `uv pip install cuga` is acceptable.

(`cuga` requires Python >= 3.10, < 3.14.) For working inside a checkout of the [cuga-agent](https://github.com/cuga-project/cuga-agent) repo itself instead of the published package:

```bash
git clone https://github.com/cuga-project/cuga-agent.git
cd cuga-agent
uv venv --python=3.12 && source .venv/bin/activate
uv sync
```

Set LLM API keys before starting anything. Use a project-local `.env`; see `docs/cuga-env-api-keys.md` for provider-specific `AGENT_SETTING_CONFIG`, `MODEL_NAME`, and API-key examples.

## Launch

```bash
uv run cuga start <service>
```

Valid `<service>` values: `demo`, `demo_skills`, `demo_crm`, `demo_docs`, `demo_health`, `demo_knowledge`, `demo_supervisor`, `travel_agent`, `manager`, `registry`, `appworld`.

- `demo` / `demo_crm` / `demo_supervisor` / `demo_knowledge` / `demo_docs` — launch the chat web UI at `http://localhost:7860` (HTTPS when SSL certificates are configured) plus a tool registry service on port 8001, each preset wiring up different sample tools (CRM+email, multi-agent supervisor, RAG knowledge, docs) so you can try the matching capability immediately.
- `demo_skills` — same UI, with cuga's own runtime skill-loading enabled (see `cuga-build-cuga-skill`).
- `manager` — a draft/publish UI: edit agent config (tools, MCP servers, LLM, policies) as a draft, try it, then publish a versioned config for production chat.
- `registry` — just the tool registry service (OpenAPI/MCP config), no chat UI.
- `appworld` / `travel_agent` — specific benchmark/example scenarios.

Other useful commands:
- `cuga stop <service>` — stop a running service.
- `cuga status` — show what's currently running.
- `cuga doctor` — GPU stack diagnosis; use CLI help and import checks for general setup problems.
- `cuga viz` — trajectory viewer dashboard (see `cuga-debug-trajectory`).

Current CUGA exposes `cuga policy` and `cuga knowledge`; inspect `uv run cuga policy --help` and `uv run cuga knowledge --help` for the installed version. The policy CLI operates on policy storage; do not assume it updates a managed agent's draft/published config. `cuga knowledge` includes config export/import and adaptation/glossary commands that can target a server. See `cuga-managed-server` for the draft → test → publish workflow.

## Next step

For embedded Python code use `cuga-build-agent`. For managed deployment use `cuga-managed-server`; test the draft and publish before checking production chat. Verify service/flag availability with `uv run cuga start --help` for the installed version.
