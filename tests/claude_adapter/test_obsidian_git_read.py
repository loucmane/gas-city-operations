"""Descendant-execution oracles for the shared observer Git policy."""

import os
from pathlib import Path
import subprocess

import pytest

from aegis_foundation.git_read import run_git_read
from aegis_foundation.obsidian_install import build_runtime_bytes

ROOT = Path(__file__).resolve().parents[2]


def _home_environment(home):
    # The suite normally suppresses config; these fixtures explicitly exercise it.
    return {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            "HOME": str(home), "XDG_CONFIG_HOME": str(home), "GIT_OPTIONAL_LOCKS": "0"}


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


@pytest.mark.parametrize("scope", ["global", "system"])
def test_safe_directory_trust_survives_hardening(tmp_path, monkeypatch, scope):
    """Real Git's ownership check, with no chown or host config changes."""
    from aegis_foundation import git_read

    repo = tmp_path / "repo"
    home = tmp_path / "home"
    home.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    config = home / (".gitconfig" if scope == "global" else "system.gitconfig")
    environment = _home_environment(home)
    real_run = subprocess.run

    def ownership_check(argv, **kwargs):
        child_env = {**kwargs.pop("env"), "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}
        if scope == "system":
            # Model a different compiled-in system config without writing /etc.
            child_env.setdefault("GIT_CONFIG_SYSTEM", str(config))
        return real_run(argv, env=child_env, **kwargs)

    untrusted = ownership_check(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                                env=environment, capture_output=True, text=True)
    assert untrusted.returncode == 128
    assert "dubious ownership" in untrusted.stderr
    config.write_text(f'[safe]\n\tdirectory = "{repo}"\n')
    trusted = ownership_check(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                              env=environment, capture_output=True, text=True)
    assert trusted.returncode == 0
    monkeypatch.setattr(git_read.subprocess, "run", ownership_check)
    result = run_git_read(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                          env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == repo


@pytest.mark.parametrize("feature", ["fsmonitor", "textconv", "external", "clean"])
def test_home_config_programs_cannot_execute(tmp_path, feature):
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    home.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "tracked.txt").write_text("before\n")
    (repo / ".gitattributes").write_text("*.txt diff=Marker filter=Marker\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.test", "-c", "commit.gpgsign=false",
                    "commit", "-qm", "fixture"], check=True)
    marker = tmp_path / "program.executed"
    hook = tmp_path / "program"
    hook.write_text(f"#!/bin/sh\nprintf executed > '{marker}'\ncat\n")
    hook.chmod(0o755)
    configs = {
        "fsmonitor": f'[core]\nfsmonitor = "{hook}"\n',
        "textconv": f'[diff "Marker"]\ntextconv = "{hook}"\n',
        "external": f'[diff]\nexternal = "{hook}"\n',
        "clean": f'[filter "Marker"]\nclean = "{hook}"\nrequired = true\n',
    }
    (home / ".gitconfig").write_text(configs[feature])
    environment = _home_environment(home)
    (repo / "tracked.txt").write_text("after!\n")
    os.utime(repo / "tracked.txt", (1, 1))
    positive = ["status", "--porcelain=v1"] if feature in {"fsmonitor", "clean"} else ["diff"]
    subprocess.run(["git", "-C", str(repo), *positive], env=environment,
                   check=True, capture_output=True, input=b"")
    assert marker.exists(), "the raw Git control must execute the configured program"
    marker.unlink()
    for command in (["status", "--porcelain=v1"], ["show", "-s", "--format=%H %P", "HEAD"]):
        run_git_read(["git", "-C", str(repo), *command], env=environment,
                     check=True, capture_output=True, input=b"")
    assert not marker.exists()
