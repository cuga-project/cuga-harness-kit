from __future__ import annotations

import subprocess

import pytest

from cuga_harness_kit import migration
from cuga_harness_kit.cli import _write_file


@pytest.fixture
def fake_kit(tmp_path, monkeypatch):
    """Point migration.scaffold_migration at a small fake kit tree instead of the real
    packaged one."""
    kits_root = tmp_path / "kits_pkg"
    kit_dir = kits_root / "migration-skills" / "claude"
    (kit_dir / "cuga-templates" / "scripts").mkdir(parents=True)
    (kit_dir / ".claude" / "skills" / "cuga-migrator").mkdir(parents=True)
    (kit_dir / "README.md").write_text("hello\n")
    (kit_dir / "migrate.sh").write_text("#!/usr/bin/env bash\necho migrate\n")
    (kit_dir / "cuga-templates" / "scripts" / "start.sh").write_text("#!/usr/bin/env bash\necho start\n")
    (kit_dir / ".claude" / "skills" / "cuga-migrator" / "SKILL.md").write_text("---\nname: cuga-migrator\n---\nhi\n")

    monkeypatch.setattr(migration.importlib.resources, "files", lambda pkg: kits_root)
    return kit_dir


@pytest.fixture
def fake_cuga_repo(tmp_path, monkeypatch):
    """A tiny local git repo standing in for the real cuga-agent GitHub repo, so clone tests
    don't touch the network."""
    repo = tmp_path / "fake-cuga-agent.git-src"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    (repo / "sdk.py").write_text("# fake sdk\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    monkeypatch.setattr(migration, "CUGA_REPO_URL", str(repo))
    return repo


def _scaffold(cwd, **kwargs):
    written: list[str] = []
    skipped: list[str] = []
    migration.scaffold_migration("claude", cwd, written=written, skipped=skipped, write_file=_write_file, **kwargs)
    return written, skipped


def test_scaffold_migration_writes_kit_tree_into_cwd(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()

    _scaffold(cwd, force=False, dry_run=False)

    assert (cwd / "README.md").read_text() == "hello\n"
    assert (cwd / ".claude" / "skills" / "cuga-migrator" / "SKILL.md").is_file()
    assert not (cwd / "migration-skills").exists()


def test_scaffold_migration_sets_scripts_executable_including_nested(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()

    _scaffold(cwd, force=False, dry_run=False)

    assert (cwd / "migrate.sh").stat().st_mode & 0o111
    assert (cwd / "cuga-templates" / "scripts" / "start.sh").stat().st_mode & 0o111


def test_scaffold_migration_skips_hand_edited_file_without_force(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()
    readme = cwd / "README.md"
    readme.write_text("hand-edited content")

    _scaffold(cwd, force=False, dry_run=False)

    assert readme.read_text() == "hand-edited content"


def test_scaffold_migration_dry_run_writes_nothing(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()

    _scaffold(cwd, force=False, dry_run=True)

    assert not (cwd / "README.md").exists()
    assert not (cwd / "migrate.sh").exists()


def test_scaffold_migration_creates_migration_from_gitkeep_when_missing(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()

    _scaffold(cwd, force=False, dry_run=False)

    assert (cwd / "migration_from" / ".gitkeep").is_file()


def test_scaffold_migration_leaves_existing_migration_from_alone(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    migration_from = cwd / "migration_from" / "some-source"
    migration_from.mkdir(parents=True)
    (migration_from / "marker.txt").write_text("pre-existing\n")

    _scaffold(cwd, force=False, dry_run=False)

    assert (migration_from / "marker.txt").read_text() == "pre-existing\n"
    assert not (cwd / "migration_from" / ".gitkeep").exists()


def test_scaffold_migration_creates_empty_user_request_placeholder(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    cwd.mkdir()

    written, _ = _scaffold(cwd, force=False, dry_run=False)

    request_file = cwd / ".cuga-migrator" / "user_request.md"
    assert request_file.read_text() == "# User Request\n"
    assert str(request_file) in written


def test_scaffold_migration_never_overwrites_existing_user_request(tmp_path, fake_kit):
    cwd = tmp_path / "project"
    request_file = cwd / ".cuga-migrator" / "user_request.md"
    request_file.parent.mkdir(parents=True)
    request_file.write_text("# User Request\nuse the one_agent architecture\n")

    written, skipped = _scaffold(cwd, force=True, dry_run=False)

    assert request_file.read_text() == "# User Request\nuse the one_agent architecture\n"
    assert str(request_file) not in written
    assert any(str(request_file) in line for line in skipped)


def test_clone_cuga_sdk_clones(tmp_path, fake_cuga_repo):
    cwd = tmp_path / "project"
    cwd.mkdir()

    migration.clone_cuga_sdk(cwd, ref=None)

    sdk_dir = cwd / migration.SDK_SUBDIR
    assert (sdk_dir / "sdk.py").read_text() == "# fake sdk\n"


def test_clone_cuga_sdk_does_not_reclone_if_already_present(tmp_path, fake_cuga_repo):
    cwd = tmp_path / "project"
    sdk_dir = cwd / migration.SDK_SUBDIR
    sdk_dir.mkdir(parents=True)
    (sdk_dir / "my_local_edit.py").write_text("keep me\n")

    migration.clone_cuga_sdk(cwd, ref=None)

    assert (sdk_dir / "my_local_edit.py").read_text() == "keep me\n"
    assert not (sdk_dir / "sdk.py").exists()


def test_clone_cuga_sdk_failure_is_non_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(migration, "CUGA_REPO_URL", "/nonexistent/not-a-repo")
    cwd = tmp_path / "project"
    cwd.mkdir()

    migration.clone_cuga_sdk(cwd, ref=None)

    assert not (cwd / migration.SDK_SUBDIR / "sdk.py").exists()
