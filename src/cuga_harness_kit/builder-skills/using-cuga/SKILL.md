---
name: using-cuga
description: Use when starting a CUGA application or setting up CUGA for the first time. Verify LLM configuration, understand what the user wants to build, and help them choose the embedded SDK or managed server before implementation.
---

# Using CUGA

Start a new build by establishing a working LLM configuration, then the user's goal and execution path. Reuse choices and successful checks already provided in the conversation. For a focused change to an existing working app, continue its established setup instead of repeating onboarding.

## 1. Establish LLM readiness

Inspect the project and the CUGA version being used. For a local SDK app or local managed server, use `cuga-install-and-launch` if CUGA is missing from the project environment. An existing remote server can be accessed through its UI/HTTP APIs without installing the SDK locally. Read `docs/cuga-env-api-keys.md` for the provider configuration examples scaffolded by this kit.

Identify where this application gets its LLM configuration:

| Existing setup | Check |
|---|---|
| Local SDK or new local server | Project environment / `.env`, selected model settings, or the SDK's explicit `model=` instance |
| Existing managed server | The selected agent's saved LLM config and server-side credentials; the local client does not need its own provider key |

Preserve an existing provider and model. If none is selected, ask which provider the user wants: WatsonX, OpenAI, or another supported provider. Ask for provider/model choices and missing configuration names; have the user place credential values in their local `.env` or supported server secret configuration. Never ask them to paste API keys into chat, print credential values, or overwrite an existing `.env`.

For environment-based setup, use the installed provider settings and this reference:

| Provider | `AGENT_SETTING_CONFIG` | Required configuration |
|---|---|---|
| WatsonX | `settings.watsonx.toml` | `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID` or `WATSONX_SPACE_ID`, chosen `MODEL_NAME` |
| OpenAI | `settings.openai.toml` | `OPENAI_API_KEY`, chosen `MODEL_NAME` |
| OpenAI-compatible endpoint | `settings.openai.toml` | Endpoint's key, `OPENAI_BASE_URL`, endpoint's `MODEL_NAME` |
| Azure OpenAI, Groq, OpenRouter | Matching bundled settings file | Use the provider-specific variables in `docs/cuga-env-api-keys.md`; verify the installed settings |

Keep provider credentials on the application's Python backend or CUGA server; a browser UI calls that backend/server and must not receive the provider key. Keep `.env` and config files containing credentials out of Git. Check configuration presence without displaying secrets. A present key, successful import, or constructed model does not establish that authentication and inference work.

### Enable the tracker and set trajectory storage

When creating a `.env` for a local SDK app or local managed server, include these settings alongside the chosen provider configuration. For an existing `.env`, add missing settings without replacing credentials or intentional user overrides.

```env
DYNACONF_ADVANCED_FEATURES__TRACKER_ENABLED=true
CUGA_LOGGING_DIR="./.cuga/logging"
```

The tracker flag is a Dynaconf setting. The directory uses `CUGA_LOGGING_DIR`, not a Dynaconf trajectory-path setting: CUGA stores trajectories under `<CUGA_LOGGING_DIR>/trajectory_data`. The relative example assumes launch from the project root; use an absolute writable path when the working directory can change. Keep the chosen logging directory out of Git (add `.cuga/logging/` to `.gitignore` for this example).

Load `.env` into the process environment **before importing CUGA**: the reviewed runtime resolves logging paths before its internal dotenv loader runs. Use `uv run --env-file .env python app.py` for an SDK app or `uv run --env-file .env cuga start manager` for a local managed server; an application bootstrap can instead call `load_dotenv()` before any CUGA import. Exported shell/service variables take precedence over `.env`; check conflicting tracker/path values if verification still shows tracking disabled or the wrong directory. Restart an already-running process after changing these settings. For a remote managed-server client, trajectory storage belongs on the server; do not create local tracker configuration merely to connect.

Verify `settings.advanced_features.tracker_enabled` is true and `cuga.config.TRAJECTORY_DATA_DIR` resolves to the intended writable directory. After the first agent run, confirm a trajectory file was actually written there; the direct model readiness check below does not produce an agent trajectory.

### Verify a model request

For the local environment-based path, run this Python example from the project environment (`uv run --env-file .env python llm_smoke.py` after saving it). It uses the same model factory and code-model settings as the SDK, including configured provider timeouts. For an explicit SDK `model=`, test that actual instance instead. For an existing managed server, use `cuga-managed-server` to test the selected agent through its UI/HTTP API: use draft chat when configuring a draft with manage access, or the existing published agent when the user only has chat/API access. Do not require admin credentials for a client-only integration. A local factory check does not verify a server's saved LLM config, and a readiness check must not publish or replace that config.

```python
import asyncio

from cuga.backend.llm.load_test_mock import is_mock_llm_enabled
from cuga.backend.llm.models import LLMManager
from cuga.config import settings


async def main():
    if is_mock_llm_enabled():
        raise RuntimeError("Mock LLM mode cannot verify provider readiness")
    model = LLMManager().get_model(settings.agent.code.model)
    reply = await model.ainvoke("Reply with a short greeting.")
    if not reply.content:
        raise RuntimeError("The configured LLM returned no content")
    print("Configured LLM request succeeded")


asyncio.run(main())
```

This checks the configured code model. If the application uses different models/endpoints for other agent nodes, check each distinct configuration too. Do not select a different model merely to make the check pass. A scripted/mock endpoint validates the protocol only; report that distinction instead of claiming real provider credentials were verified.

If the request fails, report the redacted error and address its actual cause: credentials, WatsonX project/space access, model/deployment availability, endpoint/API version, network, or quota. Verify the correction once; stop retrying an unchanged failure. If credentials or service access remain unavailable, ask the user to configure them and mark LLM readiness as unverified. Continue useful local design/scaffolding work, but do not claim agent execution works.

## 2. Understand what the user wants to build

Once readiness is established, ask what the agent should do and how people will use it, unless the user has already explained this. For example: “What do you want to build with CUGA, and will users access it through your own app/UI, the CUGA UI, or another service?” Identify the needed tools, documents and integrations from that goal. Determine whether one agent can handle it or the user needs a supervisor coordinating specialists; multi-agent composition stays within the chosen SDK/server path.

## 3. Choose SDK or managed server with the user

Explain the tradeoff in terms of their application:

| Path | Fits | Configuration and operation |
|---|---|---|
| Embedded Python SDK | A custom application with its own UI/backend, integration into an existing Python service, or direct control of the agent lifecycle | Construct `CugaAgent` / `CugaSupervisor` in the application's process; configure models, tools and policies in code; the application owns its UI and hosting |
| Managed server | A CUGA service with Manage UI, stored/versioned configuration, draft testing and publishing, used from the built-in UI or HTTP clients | Configure a selected agent in Manage or through HTTP; test its draft, publish a version, then invoke the published agent |

A custom UI generally makes SDK embedding a useful recommendation, but it can also call a managed server over HTTP. The SDK does not provide that custom UI automatically. Respect an explicit mode choice; otherwise recommend the path that fits the goal and ask the user to choose before generating mode-specific implementation or launching services. Do not silently choose SDK or server based only on the word “agent” or “UI”.

| Selected path | Continue with |
|---|---|
| SDK | `cuga-build-agent`; keep the user's chosen app/UI architecture |
| Managed server | `cuga-managed-server`; distinguish local authoritative JSON, saved draft and published config |

For a supervisor or multiple specialist agents, also follow `cuga-build-supervisor` in the selected mode. Read the selected skill's full instructions. SDK construction and local `.cuga/` files do not automatically update managed-server config. Add the matching tool, policy, runtime-skill or knowledge skill when the user's build needs it. Report the provider/model checked, readiness evidence, selected mode and concrete next implementation step without exposing credentials.
