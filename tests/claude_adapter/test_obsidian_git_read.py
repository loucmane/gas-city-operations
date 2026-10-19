"""Descendant-execution oracles for the shared observer Git policy."""

import os
from pathlib import Path
import subprocess

import pytest

from aegis_foundation.git_read import run_git_read
from aegis_foundation.obsidian_install import build_runtime_bytes

ROOT = Path(__file__).resolve().parents[2]


def test_plugin_and_zipapp_share_the_exact_git_policy():
    import io
    import zipfile

    policy = (ROOT / "aegis_foundation/git_read.py").read_bytes()
    assert (ROOT / "plugins/gas-city-workflow/scripts/_git_read.py").read_bytes() == policy
    with zipfile.ZipFile(io.BytesIO(build_runtime_bytes(ROOT))) as archive:
        assert archive.read("aegis_foundation/git_read.py") == policy


@pytest.mark.parametrize("scope", ["local", "global", "inherited"])
def test_status_neutralizes_fsmonitor_in_every_config_scope(tmp_path, scope):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    marker = tmp_path / "fsmonitor.executed"
    hook = tmp_path / "fsmonitor"
    hook.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\n")
    hook.chmod(0o755)
    environment = dict(os.environ)
    if scope == "local":
        subprocess.run(["git", "-C", str(repo), "config", "core.fsmonitor", str(hook)], check=True)
    elif scope == "global":
        config = tmp_path / "global.gitconfig"
        config.write_text(f'[core]\nfsmonitor = "{hook}"\n')
        environment["GIT_CONFIG_GLOBAL"] = str(config)
    else:
        environment.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
                            "GIT_CONFIG_VALUE_0": str(hook)})
    # Positive control: the same configuration really launches the shell.
    subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v1"],
                   env=environment, check=True, capture_output=True)
    assert marker.exists()
    marker.unlink()
    result = run_git_read(["git", "-C", str(repo), "status", "--porcelain=v1"],
                          env=environment, check=True, capture_output=True)
    assert result.returncode == 0
    assert not marker.exists()


def test_status_neutralizes_included_clean_filter_and_required_process(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "tracked.txt").write_text("before\n")
    (repo / ".gitattributes").write_text("*.txt filter=Marker\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    marker = tmp_path / "clean.executed"
    hook = tmp_path / "clean"
    hook.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\ncat\n")
    hook.chmod(0o755)
    config = tmp_path / "included.gitconfig"
    config.write_text(f'[filter "Marker"]\nclean = "{hook}"\nrequired = true\n')
    subprocess.run(["git", "-C", str(repo), "config", "include.path", str(config)], check=True)
    (repo / "tracked.txt").write_text("after!\n")
    os.utime(repo / "tracked.txt", (1, 1))
    subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v1"], check=True, capture_output=True)
    assert marker.exists()
    marker.unlink()
    # A configured required process would fail status unless both keys are disabled.
    with config.open("a") as output:
        output.write(f'process = "{hook}"\n')
    result = run_git_read(["git", "-C", str(repo), "status", "--porcelain=v1"],
                          check=True, capture_output=True, text=True)
    assert "tracked.txt" in result.stdout
    assert not marker.exists()


@pytest.mark.parametrize("command", [["fetch"], ["checkout", "main"],
                                     ["worktree", "add", "x"], ["remote", "update"],
                                     ["alias-from-config"], ["diff"]])
def test_unreviewed_git_commands_fail_before_execution(command):
    with pytest.raises(ValueError, match="unsupported Git observation"):
        run_git_read(["git", *command])


def test_status_refuses_submodules_instead_of_reporting_false_clean(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "update-index", "--add", "--cacheinfo",
                    "160000," + "a" * 40 + ",submodule"], check=True)
    with pytest.raises(RuntimeError, match="submodules"):
        run_git_read(["git", "-C", str(tmp_path), "status", "--porcelain=v1"],
                     check=True, capture_output=True)
