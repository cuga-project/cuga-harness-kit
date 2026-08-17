"""`cuga-harness-kit migrate run|source_sync|cuga_sync` — run the corresponding launch script in the
current directory (which `init --migration` scaffolds a migration kit's content directly into).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = {"source_sync": "source_sync.sh", "cuga_sync": "cuga_sync.sh", "run": "migrate.sh"}


def run(command: str, args: list[str], cwd: Path | None = None) -> int:
    cwd = cwd or Path.cwd()
    script = cwd / SCRIPTS[command]
    if not script.is_file():
        sys.exit(
            f"{script} not found. Run `cuga-harness-kit init --targets claude --migration` "
            "(or --targets bob) here first."
        )
    result = subprocess.run(["bash", str(script), *args], cwd=cwd)
    return result.returncode
