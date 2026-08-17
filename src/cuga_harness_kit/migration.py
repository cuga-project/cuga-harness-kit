"""`cuga-harness-kit init --migration` — scaffold the cuga-migrator subsystem (skills, subagents,
slash commands, launch scripts, cuga-templates/) for Claude Code and Bob, and optionally clone the
cuga SDK the pipeline reads reference examples from.

Unlike the guidance skills in cli.py, this content isn't rendered from a single canonical source —
the Claude and Bob migration kits are genuinely different hand-authored documents (Bob inlines the
whole pipeline into SKILL.md since it has no subagent primitive; Claude dispatches to a slash
command that spawns named subagents), so both trees are scaffolded verbatim.
"""

from __future__ import annotations

import importlib.resources
import shutil
import subprocess
from pathlib import Path
from typing import Callable

MIGRATION_TARGETS = ("claude", "bob")

CUGA_REPO_URL = "https://github.com/cuga-project/cuga-agent"
SDK_SUBDIR = Path("migration_to") / "cuga-agent"

WriteFile = Callable[..., None]


def scaffold_migration(
    target: str,
    cwd: Path,
    *,
    force: bool,
    dry_run: bool,
    written: list[str],
    skipped: list[str],
    write_file: WriteFile,
) -> None:
    """Write the `target`'s migration kit into `cwd`, one file at a time via `write_file` (the
    same helper the rest of `init` uses), so migration output gets the same per-file
    skip/force/dry-run/report semantics as everything else `init` scaffolds.
    """
    kit_src = importlib.resources.files("cuga_harness_kit") / "migration-skills" / target
    dest_paths: list[Path] = []
    with importlib.resources.as_file(kit_src) as kit_path:
        for src_file in sorted(kit_path.rglob("*")):
            if not src_file.is_file():
                continue
            dest = cwd / src_file.relative_to(kit_path)
            dest_paths.append(dest)
            write_file(dest, src_file.read_text(), force=force, dry_run=dry_run, written=written, skipped=skipped)

    if dry_run:
        return

    for dest in dest_paths:
        if dest.suffix == ".sh" and dest.is_file():
            dest.chmod(dest.stat().st_mode | 0o111)

    migration_from = cwd / "migration_from"
    if not migration_from.is_dir() or not any(migration_from.iterdir()):
        migration_from.mkdir(parents=True, exist_ok=True)
        (migration_from / ".gitkeep").touch()

    _ensure_user_request_file(cwd, written=written, skipped=skipped)


def _ensure_user_request_file(cwd: Path, *, written: list[str], skipped: list[str]) -> None:
    """Create .cuga-migrator/user_request.md with just its header if it doesn't exist yet.

    This is a standing file the user edits directly (not a per-run prompt) — the orchestrator
    reads it at the start of every migration run, even when it's empty. It's created here only so
    it's discoverable right after scaffolding, the same way CLAUDE.md/AGENTS.md are. Deliberately
    bypasses write_file's --force semantics: this file holds a user's own, possibly in-progress
    request, and must never be overwritten by `init`/`update` once it exists.
    """
    request_file = cwd / ".cuga-migrator" / "user_request.md"
    if request_file.exists():
        skipped.append(f"{request_file} (already exists — never overwritten by init/update)")
        return
    request_file.parent.mkdir(parents=True, exist_ok=True)
    request_file.write_text("# User Request\n")
    written.append(str(request_file))


def clone_cuga_sdk(cwd: Path, *, ref: str | None) -> None:
    sdk_dest = cwd / SDK_SUBDIR

    if sdk_dest.exists():
        print(f"  {SDK_SUBDIR}/ already exists — leaving it as-is (not re-cloning).")
        return

    if shutil.which("git") is None:
        print(
            f"  ⚠ git not found — skipping SDK clone. Copy it in yourself:\n"
            f"    git clone {CUGA_REPO_URL} {sdk_dest}"
        )
        return

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [CUGA_REPO_URL, str(sdk_dest)]

    print(f"  Cloning cuga SDK into {SDK_SUBDIR}/ ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(
            f"  ⚠ Failed to clone the cuga SDK — copy it in yourself:\n"
            f"    git clone {CUGA_REPO_URL} {sdk_dest}\n"
            f"    {result.stderr.strip()}"
        )
        return

    sha = subprocess.run(
        ["git", "-C", str(sdk_dest), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    print(f"  Cloned cuga SDK ({sha}) into {SDK_SUBDIR}/")
