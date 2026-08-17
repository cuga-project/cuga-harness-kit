"""Custom Hatchling build hook.

src/cuga_harness_kit/migration-skills/{claude,bob}/ are the canonical, hand-maintained migration
kits — never edited by this build. src/cuga_harness_kit/migration-skills/cuga-templates/ is shared
between them (a plain directory, not a symlink — `initialize` below copies it into each staged kit
explicitly) so it's authored once. The kit dirs live under
`packages = ["src/cuga_harness_kit"]`'s normal inclusion boundary, so both wheel and sdist targets
explicitly `exclude` the raw migration-skills/ tree in pyproject.toml (claude/ and bob/
specifically for sdist; the whole directory for wheel). Plain `force-include` doesn't filter
anything (Hatchling applies `exclude` patterns to normal inclusion mechanisms but not to
`force-include`), so this hook stages a filtered copy of each kit and force-includes the staged
copy back in instead.

Two build targets both run this hook (see pyproject.toml):

- sdist: filters fresh from migration-skills/<target>/ and bundles the filtered copy inside the
  sdist itself, under kits_staged/<target>/. This is required because `uv build` (and `python -m
  build`) build the wheel *from* the sdist, not from the original project tree — by that point
  the raw migration-skills/<target>/ tree (with its unfiltered .git/, test fixtures, etc.) isn't
  part of the sdist's own source selection, so the wheel step must read the already-filtered
  kits_staged/ copy instead of re-deriving it.
- wheel: if kits_staged/<target>/ exists (building from an sdist that already carries it), reuse
  it as-is. Otherwise (a direct/local wheel build, e.g. `uv build --wheel` or an editable
  `uv sync` straight against this project tree) filter fresh from migration-skills/<target>/, same
  as the sdist path does.
"""

from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

GENERIC_SKIP_NAMES = {".git", ".codegraph", "__pycache__", ".DS_Store", ".env"}

# Kit-specific exclusions: files that shouldn't ship even though they're generic starter content
# elsewhere, plus real local test fixtures.
KIT_FILTERS = {
    "claude": {
        "skip_dirs": {Path(".claude/hooks")},
        "skip_files_in": {Path(".claude"): ("settings.json",)},
    },
    "bob": {
        "skip_dirs": {Path("migration_from/sre-tooling-wx-sre-supervisor")},
        "skip_files_in": {Path("migration_to/data/ground_truth"): ("*.txt",)},
    },
}

KITS = {
    "claude": "src/cuga_harness_kit/migration-skills/claude",
    "bob": "src/cuga_harness_kit/migration-skills/bob",
}

SHARED_TEMPLATES = "src/cuga_harness_kit/migration-skills/cuga-templates"

SDIST_STAGING_DIR = "kits_staged"


class CugaKitsBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        staging_root = Path(self.root) / "build" / "kits"
        if staging_root.exists():
            shutil.rmtree(staging_root)

        for target, src_name in KITS.items():
            dest = staging_root / target
            pre_staged = Path(self.root) / SDIST_STAGING_DIR / target

            if pre_staged.is_dir():
                shutil.copytree(pre_staged, dest)
            else:
                src = Path(self.root) / src_name
                self._copy_filtered(src, dest, KIT_FILTERS[target])
                shutil.copytree(
                    Path(self.root) / SHARED_TEMPLATES,
                    dest / "cuga-templates",
                    ignore=shutil.ignore_patterns(*GENERIC_SKIP_NAMES),
                )
                self._ensure_migration_from(dest)

            for sh in dest.glob("*.sh"):
                sh.chmod(sh.stat().st_mode | 0o111)
            for sh in (dest / "cuga-templates").glob("**/*.sh"):
                sh.chmod(sh.stat().st_mode | 0o111)

            if self.target_name == "sdist":
                build_data.setdefault("force_include", {})[str(dest)] = f"{SDIST_STAGING_DIR}/{target}"
            else:
                build_data.setdefault("force_include", {})[str(dest)] = f"cuga_harness_kit/migration-skills/{target}"

    @staticmethod
    def _ensure_migration_from(dest: Path) -> None:
        migration_from = dest / "migration_from"
        if not migration_from.is_dir():
            migration_from.mkdir(parents=True)
            (migration_from / ".gitkeep").touch()

    @staticmethod
    def _copy_filtered(src: Path, dest: Path, filters: dict) -> None:
        skip_dirs = filters["skip_dirs"]
        skip_files_in = filters["skip_files_in"]

        def ignore(dir_path: str, names: list[str]) -> set[str]:
            rel = Path(dir_path).relative_to(src)
            ignored = {n for n in names if n in GENERIC_SKIP_NAMES}
            for skip_dir in skip_dirs:
                if rel == skip_dir.parent and skip_dir.name in names:
                    ignored.add(skip_dir.name)
            for skip_rel, patterns in skip_files_in.items():
                if rel == skip_rel:
                    for pattern in patterns:
                        ignored.update(fnmatch.filter(names, pattern))
            return ignored

        shutil.copytree(src, dest, ignore=ignore)
