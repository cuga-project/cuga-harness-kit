from __future__ import annotations

import stat

import pytest

from cuga_harness_kit import dispatch


def _make_script(cwd, script_name, body):
    script = cwd / script_name
    script.write_text(body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_run_missing_script_exits(tmp_path):
    with pytest.raises(SystemExit):
        dispatch.run("run", [], cwd=tmp_path)


def test_run_forwards_args_and_exit_code(tmp_path):
    _make_script(
        tmp_path,
        "migrate.sh",
        "#!/usr/bin/env bash\necho \"args: $@\" > out.txt\nexit 7\n",
    )

    code = dispatch.run("run", ["cp4i-res", "cp4i-cuga"], cwd=tmp_path)

    assert code == 7
    assert (tmp_path / "out.txt").read_text().strip() == "args: cp4i-res cp4i-cuga"


def test_run_source_sync_uses_its_own_script(tmp_path):
    _make_script(tmp_path, "source_sync.sh", "#!/usr/bin/env bash\nexit 0\n")

    assert dispatch.run("source_sync", [], cwd=tmp_path) == 0


def test_run_cuga_sync_uses_its_own_script(tmp_path):
    _make_script(tmp_path, "cuga_sync.sh", "#!/usr/bin/env bash\nexit 3\n")

    assert dispatch.run("cuga_sync", [], cwd=tmp_path) == 3
