---
name: cuga-build-cuga-skill
description: Use when the user wants a running CugaAgent to load a new capability at runtime via cuga's own skill system, e.g. "add a skill to my agent", "create a .cuga/skills SKILL.md", "how does load_skill work".
---

# Authoring a cuga runtime skill

This is different from the IDE-assistant skill you're reading right now. **cuga's own agents** can discover and load `SKILL.md` files at runtime via a `load_skill` tool — this skill teaches you how to author one of those.

## Where skills live

Controlled by `[skills] root` in `settings.toml` (or `DYNACONF_SKILLS__ROOT`):

| `root` value | Directory | Notes |
|---|---|---|
| `cuga` (default) | `.cuga/skills/` | cuga's own convention, avoids colliding with `.agents/skills/` written by other tools |
| `agents` | `.agents/skills/` | shared convention used by e.g. `npx skills` |
| `global_agents` | `~/.config/agents/skills/` | global, not project-scoped |
| `global_cuga` | `~/.config/cuga/skills/` | legacy global path |

Skills are discovered recursively (`**/SKILL.md`) under whichever root is active.

## SKILL.md shape (cuga runtime contract)

Required frontmatter: **`name`** and **`description`** (shown to the agent in its available-skills list — write a description the agent can use to decide when to load it). Optional **`requirements`**: a pip/npm package or list of packages the skill needs installed. Everything below the frontmatter is arbitrary markdown — the full instruction text handed back by `load_skill` when the agent loads this skill.

```markdown
---
name: my-skill
description: Use when the user asks to <do X>. Loads instructions for <Y>.
requirements: some-pip-package
---

# My Skill

Step-by-step instructions, code snippets, examples — whatever the agent
needs in its context to actually perform the task.
```

Name validation: no path separators or `..` in `name` — cuga sanitizes/rejects unsafe or Jinja2-template-injected values in `name`/`description` for prompt-injection safety.

## Try it

```bash
uv run cuga start demo_skills
```

Runs with `[advanced_features] sandbox_mode = "native"` by default. For sandboxed execution instead: `uv sync --extra opensandbox` then use the `opensandbox` mode, or `uv sync --group sandbox` + `uv run cuga start demo --sandbox` with `[skills]` enabled for Docker/Podman isolation.

## Installing a ready-made skill

Anthropic publishes ready-made skill folders (e.g. `pptx`) that follow the same `SKILL.md` convention:

```bash
npx skills add https://github.com/anthropics/skills --skill pptx -a universal
```

This drops it under `.agents/skills/pptx/SKILL.md`. To use cuga's default layout instead, copy/symlink it into `.cuga/skills/`. Add `-g` to install globally. Restart `uv run cuga start demo_skills` (or your app) afterward so skills are rescanned — there's no hot-reload.

## Don't confuse this with policies

A runtime skill is instructional content the agent chooses to load. A policy (playbook, intent guard, etc. — see `cuga-author-policy`) is a rule the runtime *enforces* on the agent regardless of whether it "chooses" to. Use a skill for optional know-how, a policy for a constraint or workflow that must always apply.
