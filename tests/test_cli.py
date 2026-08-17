from pathlib import Path

import pytest

from cuga_harness_kit import migration
from cuga_harness_kit.cli import init


def test_init_skips_differing_files_without_force(tmp_path: Path):
    dest = tmp_path / ".claude" / "skills" / "getting-started" / "SKILL.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("hand-edited content")

    init(["claude"], force=False, dry_run=False, cwd=tmp_path)

    assert dest.read_text() == "hand-edited content"


def test_update_overwrites_differing_files(tmp_path: Path):
    dest = tmp_path / ".claude" / "skills" / "getting-started" / "SKILL.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("stale content from an older cuga-harness-kit version")

    init(["claude"], force=True, dry_run=False, cwd=tmp_path)

    assert "cuga-getting-started" in dest.read_text()


def test_init_writes_env_api_key_guide(tmp_path: Path):
    init(["claude"], force=False, dry_run=False, cwd=tmp_path)

    guide = tmp_path / "docs" / "cuga-env-api-keys.md"
    assert guide.is_file()
    text = guide.read_text()
    assert 'AGENT_SETTING_CONFIG="settings.groq.toml"' in text
    assert 'AGENT_SETTING_CONFIG="settings.openai.toml"' in text


@pytest.fixture
def fake_migration_kit(tmp_path, monkeypatch):
    kits_root = tmp_path / "kits_pkg"
    kit_dir = kits_root / "migration-skills" / "claude"
    (kit_dir / ".claude" / "skills" / "cuga-migrator").mkdir(parents=True)
    (kit_dir / ".claude" / "skills" / "cuga-migrator" / "SKILL.md").write_text("---\nname: cuga-migrator\n---\nhi\n")
    (kit_dir / "migrate.sh").write_text("#!/usr/bin/env bash\necho migrate\n")

    monkeypatch.setattr(migration.importlib.resources, "files", lambda pkg: kits_root)


def test_init_without_migration_flag_skips_migration_content(tmp_path: Path, fake_migration_kit):
    init(["claude"], force=False, dry_run=False, cwd=tmp_path)

    assert not (tmp_path / ".claude" / "skills" / "cuga-migrator").exists()
    assert not (tmp_path / "migrate.sh").exists()


def test_init_with_migration_flag_scaffolds_migration_content(tmp_path: Path, fake_migration_kit):
    init(["claude"], force=False, dry_run=False, cwd=tmp_path, with_migration=True, skip_sdk=True)

    assert (tmp_path / ".claude" / "skills" / "cuga-migrator" / "SKILL.md").is_file()
    assert (tmp_path / "migrate.sh").is_file()
    # --migration is exclusive — it replaces the guidance skills for this run, doesn't add to them
    assert not (tmp_path / ".claude" / "skills" / "getting-started").exists()
    assert not (tmp_path / "docs" / "cuga-env-api-keys.md").exists()


def test_init_migration_flag_has_no_effect_for_unsupported_targets(tmp_path: Path, fake_migration_kit):
    init(["cursor"], force=False, dry_run=False, cwd=tmp_path, with_migration=True, skip_sdk=True)

    assert not (tmp_path / "migrate.sh").exists()
    # --migration is exclusive, so cursor's own guidance rules aren't written either — the whole
    # run scaffolds nothing when none of the requested targets support migration
    assert not (tmp_path / ".cursor").exists()
