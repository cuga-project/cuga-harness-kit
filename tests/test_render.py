import re

import pytest
import yaml

from cuga_harness_kit.cli import SKILLS_DIR, _skill_dirs
from cuga_harness_kit.render import parse_skill_md, render_agents_section, render_mdc

pytestmark = pytest.mark.unit

GETTING_STARTED = SKILLS_DIR / "getting-started" / "SKILL.md"


def test_all_skills_have_required_frontmatter():
    skill_paths = _skill_dirs()
    assert len(skill_paths) == 9
    for skill_path in skill_paths:
        frontmatter, body = parse_skill_md(skill_path / "SKILL.md")
        assert frontmatter["name"], skill_path
        assert frontmatter["description"], skill_path
        assert body.strip(), skill_path


def test_render_mdc_shape():
    frontmatter, _ = parse_skill_md(GETTING_STARTED)
    mdc = render_mdc(GETTING_STARTED)

    match = re.match(r"\A---\n(.*?)\n---\n\n(.*)", mdc, re.DOTALL)
    assert match, mdc
    parsed_header = yaml.safe_load(match.group(1))
    assert parsed_header["alwaysApply"] is False
    assert parsed_header["description"] == frontmatter["description"]
    assert "# Getting started with cuga" in match.group(2)


def test_render_agents_section_shape():
    frontmatter, _ = parse_skill_md(GETTING_STARTED)
    section = render_agents_section(GETTING_STARTED)

    assert section.startswith(f"## {frontmatter['name']}\n")
    assert f"_{frontmatter['description']}_" in section
    assert "---" not in section.splitlines()[0]
    # body headings are demoted by one level so they don't collide with the
    # top-level "## <name>" wrapper this section lives under
    assert "### Two different meanings" in section


def test_render_is_pure_and_repeatable():
    assert render_mdc(GETTING_STARTED) == render_mdc(GETTING_STARTED)
    assert render_agents_section(GETTING_STARTED) == render_agents_section(
        GETTING_STARTED
    )


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_codex_preserves_fenced_templates(tmp_path, fence):
    path = tmp_path / "SKILL.md"
    inner_fence = "```" if fence.startswith("~") else "~~~"
    body = f"# Outer\n\n{fence}markdown\n# Runtime skill\n## Instructions\n{inner_fence}\n{fence}\n\n## After\n"
    path.write_text("---\nname: fixture\ndescription: fixture\n---\n" + body)
    rendered = render_agents_section(path)
    assert "## Outer" in rendered
    assert (
        f"{fence}markdown\n# Runtime skill\n## Instructions\n{inner_fence}\n{fence}"
        in rendered
    )
    assert "### After" in rendered


def test_all_documented_python_blocks_compile():
    import ast

    for folder in _skill_dirs():
        _, body = parse_skill_md(folder / "SKILL.md")
        for index, source in enumerate(
            re.findall(r"^```python\n(.*?)^```", body, re.MULTILINE | re.DOTALL)
        ):
            compile(
                source,
                f"{folder.name}:example-{index}",
                "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )


def test_all_targets_include_managed_workflow_and_preserve_examples(tmp_path):
    from cuga_harness_kit.cli import init

    init(["claude", "cursor", "codex", "bob"], force=False, dry_run=False, cwd=tmp_path)
    for path in (
        tmp_path / ".claude/skills/managed-server/SKILL.md",
        tmp_path / ".bob/skills/managed-server/SKILL.md",
        tmp_path / ".cursor/rules/cuga-managed-server.mdc",
        tmp_path / "AGENTS.md",
    ):
        content = path.read_text()
        assert "POST /api/manage/config" in content
        assert (
            "cuga-managed-server" in content
            or "# Building with the managed server" in content
        )
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "# Budget Analysis Workflow\n\n1. Read the budget." in agents
    assert "# My Skill" in agents
