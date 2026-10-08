"""Render a canonical Claude SKILL.md into Cursor .mdc or a Codex AGENTS.md section.

Claude and Bob both read skills as a per-skill directory + SKILL.md with
frontmatter, so those two targets use the SKILL.md file verbatim. Cursor
(single rule file + frontmatter) and Codex (one shared file, no frontmatter)
need different shapes, which are derived from the canonical SKILL.md here,
at scaffold time, so there's a single source of truth per skill.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,5})(\s)")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def parse_skill_md(skill_md_path: Path) -> tuple[dict, str]:
    """Split a SKILL.md file into (frontmatter dict, body markdown)."""
    text = skill_md_path.read_text()
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{skill_md_path} has no YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip("\n")
    return frontmatter, body


def render_mdc(skill_md_path: Path) -> str:
    """SKILL.md -> Cursor .mdc content: same description, alwaysApply: false, body verbatim."""
    frontmatter, body = parse_skill_md(skill_md_path)
    header = yaml.safe_dump(
        {"description": frontmatter["description"], "alwaysApply": False},
        sort_keys=False,
        allow_unicode=True,
    ).strip()
    return f"---\n{header}\n---\n\n{body}\n"


def render_agents_section(skill_md_path: Path) -> str:
    """SKILL.md -> one '## <name>' section for AGENTS.md, headings demoted one level."""
    frontmatter, body = parse_skill_md(skill_md_path)
    # Code fences contain runnable Python, YAML and runtime skill templates.
    # Demoting their headings changes the example rather than its presentation.
    lines = []
    fence_char = None
    fence_length = 0
    for line in body.splitlines(keepends=True):
        fence = _FENCE_RE.match(line)
        if fence_char is None:
            if fence:
                fence_char = fence[1][0]
                fence_length = len(fence[1])
            else:
                line = _HEADING_RE.sub(r"#\1\2", line)
        elif (
            fence
            and fence[1][0] == fence_char
            and len(fence[1]) >= fence_length
            and not fence[2].strip()
        ):
            fence_char = None
        lines.append(line)
    demoted = "".join(lines)
    return f"## {frontmatter['name']}\n\n_{frontmatter['description']}_\n\n{demoted}\n"
