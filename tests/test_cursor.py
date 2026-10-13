from pathlib import Path

import pytest

from cuga_harness_kit.cli import SKILLS_DIR, _skill_dirs, init
from cuga_harness_kit.render import parse_skill_md, render_mdc

pytestmark = pytest.mark.unit

SOURCE = SKILLS_DIR / "build-agent" / "SKILL.md"


def legacy_rule(root: Path, content: str) -> Path:
    path = root / ".cursor/rules/cuga-build-agent.mdc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def native_skill(root: Path) -> Path:
    return root / ".cursor/skills/cuga-build-agent/SKILL.md"


def test_cursor_installs_all_native_skills_with_matching_names(tmp_path):
    init(["cursor"], force=False, dry_run=False, cwd=tmp_path)

    for folder in _skill_dirs():
        source = folder / "SKILL.md"
        frontmatter, _ = parse_skill_md(source)
        installed = tmp_path / ".cursor/skills" / frontmatter["name"] / "SKILL.md"
        assert installed.read_bytes() == source.read_bytes()
        assert installed.parent.name == frontmatter["name"]
    assert not (tmp_path / ".cursor/rules").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".bob").exists()
    assert not (tmp_path / "AGENTS.md").exists()


@pytest.mark.parametrize("force", [False, True])
def test_generated_rule_is_removed_after_native_skill_installed(tmp_path, force):
    legacy = legacy_rule(tmp_path, render_mdc(SOURCE))
    unrelated = legacy.parent / "project-style.mdc"
    unrelated.write_text("Always follow our project conventions.")

    init(["cursor"], force=force, dry_run=False, cwd=tmp_path)

    assert native_skill(tmp_path).read_bytes() == SOURCE.read_bytes()
    assert not legacy.exists()
    assert not list(legacy.parent.glob("*.bak*"))
    assert unrelated.read_text() == "Always follow our project conventions."
    init(["cursor"], force=force, dry_run=False, cwd=tmp_path)
    assert not list(legacy.parent.glob("*.bak*"))


@pytest.mark.parametrize("force", [False, True])
def test_edited_rule_is_backed_up_without_overwriting_existing_backup(
    tmp_path, force, capsys
):
    content = render_mdc(SOURCE) + "\nOur custom workflow.\n"
    legacy = legacy_rule(tmp_path, content)
    backup = legacy.with_name(legacy.name + ".bak")
    backup.write_text("Earlier backup")

    init(["cursor"], force=force, dry_run=False, cwd=tmp_path)

    assert native_skill(tmp_path).read_bytes() == SOURCE.read_bytes()
    assert not legacy.exists()
    assert backup.read_text() == "Earlier backup"
    saved = legacy.with_name(legacy.name + ".bak.1")
    assert saved.read_text() == content
    assert str(saved) in capsys.readouterr().out
    init(["cursor"], force=force, dry_run=False, cwd=tmp_path)
    assert len(list(legacy.parent.glob("*.bak*"))) == 2


@pytest.mark.parametrize("edited", [False, True])
def test_cursor_migration_dry_run_does_not_change_files(tmp_path, edited, capsys):
    content = render_mdc(SOURCE) + ("\nCustom instruction.\n" if edited else "")
    legacy = legacy_rule(tmp_path, content)
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }

    init(["cursor"], force=False, dry_run=True, cwd=tmp_path)

    after = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert after == before
    assert not native_skill(tmp_path).exists()
    assert not list(legacy.parent.glob("*.bak*"))
    output = capsys.readouterr().out
    assert "migrated:" in output
    assert "dry-run" in output


def test_conflicting_native_skill_preserves_legacy_rule_without_force(tmp_path):
    legacy = legacy_rule(tmp_path, render_mdc(SOURCE))
    native = native_skill(tmp_path)
    native.parent.mkdir(parents=True)
    native.write_text("Hand-edited native skill")

    init(["cursor"], force=False, dry_run=False, cwd=tmp_path)

    assert native.read_text() == "Hand-edited native skill"
    assert legacy.read_text() == render_mdc(SOURCE)


def test_force_installs_native_skill_before_retiring_legacy_rule(tmp_path):
    legacy = legacy_rule(tmp_path, "Older rule content")
    native = native_skill(tmp_path)
    native.parent.mkdir(parents=True)
    native.write_text("Existing native skill")

    init(["cursor"], force=True, dry_run=False, cwd=tmp_path)

    assert native.read_bytes() == SOURCE.read_bytes()
    assert not legacy.exists()
    assert legacy.with_name(legacy.name + ".bak").read_text() == "Older rule content"


def test_other_targets_leave_cursor_legacy_rules_active(tmp_path):
    legacy = legacy_rule(tmp_path, render_mdc(SOURCE))

    init(["claude", "codex", "bob"], force=False, dry_run=False, cwd=tmp_path)

    assert legacy.read_text() == render_mdc(SOURCE)
    assert not native_skill(tmp_path).exists()


def test_symlinked_legacy_rule_is_reported_and_preserved(tmp_path, capsys):
    target = tmp_path / "shared-rule.mdc"
    target.write_text(render_mdc(SOURCE))
    legacy = tmp_path / ".cursor/rules/cuga-build-agent.mdc"
    legacy.parent.mkdir(parents=True)
    legacy.symlink_to(target)

    init(["cursor"], force=False, dry_run=False, cwd=tmp_path)

    assert native_skill(tmp_path).read_bytes() == SOURCE.read_bytes()
    assert legacy.is_symlink()
    assert target.read_text() == render_mdc(SOURCE)
    assert "symlink — migrate manually" in capsys.readouterr().out


@pytest.mark.parametrize("parent", [".cursor", ".cursor/rules"])
def test_symlinked_legacy_directory_keeps_shared_rules(tmp_path, capsys, parent):
    shared = tmp_path / "shared"
    shared.mkdir()
    link = tmp_path / parent
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(shared, target_is_directory=True)
    legacy = legacy_rule(tmp_path, render_mdc(SOURCE))

    init(["cursor"], force=False, dry_run=False, cwd=tmp_path)

    assert legacy.read_text() == render_mdc(SOURCE)
    assert not list(shared.rglob("*.bak*"))
    assert "symlink — migrate manually" in capsys.readouterr().out


@pytest.mark.parametrize("newline", [b"\r\n", b"\r"])
def test_newline_only_legacy_edits_are_preserved_exactly(tmp_path, newline):
    content = render_mdc(SOURCE).encode().replace(b"\n", newline)
    legacy = legacy_rule(tmp_path, "")
    legacy.write_bytes(content)

    init(["cursor"], force=False, dry_run=False, cwd=tmp_path)

    assert not legacy.exists()
    assert legacy.with_name(legacy.name + ".bak").read_bytes() == content


def test_cursor_preserves_canonical_source_bytes(tmp_path, monkeypatch):
    import cuga_harness_kit.cli as cli

    source = tmp_path / "sources/example/SKILL.md"
    source.parent.mkdir(parents=True)
    content = b"---\r\nname: example\r\ndescription: Example skill\r\n---\r\n\r\n# Example\r\n"
    source.write_bytes(content)
    monkeypatch.setattr(cli, "SKILLS_DIR", source.parent.parent)
    project = tmp_path / "project"
    project.mkdir()

    init(["cursor"], force=False, dry_run=False, cwd=project)

    native = project / ".cursor/skills/example/SKILL.md"
    assert native.read_bytes() == content
    native.write_bytes(content.replace(b"\r\n", b"\n"))
    init(["cursor"], force=False, dry_run=False, cwd=project)
    assert native.read_bytes() != content
    init(["cursor"], force=True, dry_run=False, cwd=project)
    assert native.read_bytes() == content
