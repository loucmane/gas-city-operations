"""Execute shipped entrypoints against poisoned caches in disposable fixtures."""

from __future__ import annotations

import importlib.util
import json
import marshal
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def poison(source: Path, marker: Path) -> tuple[Path, bytes]:
    """Build a timestamp-valid adversarial cache, without loading it here."""
    cache = source.parent / "__pycache__" / f"{source.stem}.{sys.implementation.cache_tag}.pyc"
    cache.parent.mkdir(exist_ok=True)
    code = compile(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('poison')\n"
        "raise RuntimeError('adversarial cache executed')\n",
        str(source),
        "exec",
    )
    data = (
        importlib.util.MAGIC_NUMBER
        + struct.pack("<III", 0, int(source.stat().st_mtime), source.stat().st_size)
        + marshal.dumps(code)
    )
    cache.write_bytes(data)
    return cache, data


def clean_environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in ("PYTHONPYCACHEPREFIX", "PYTHONDONTWRITEBYTECODE", "AEGIS_SOURCE_ROOT"):
        env.pop(name, None)
    return env


@pytest.mark.parametrize("packaged", [False, True])
def test_hook_entrypoint_ignores_poison_before_runtime_imports(tmp_path, packaged):
    relative = Path(".claude/scripts/gate_lib.py")
    source = ROOT / "aegis_foundation/assets" / relative if packaged else ROOT / relative
    wrapper = tmp_path / relative
    wrapper.parent.mkdir(parents=True)
    wrapper.write_bytes(source.read_bytes())
    runtime = tmp_path / "aegis_foundation/gate/hooks/__init__.py"
    runtime.parent.mkdir(parents=True)
    runtime.write_text(
        "import os, sys, json, subprocess, importlib.util\n"
        "from pathlib import Path\n"
        "__all__ = ['main']\n"
        "def main():\n"
        "    root=Path(__file__).parents[3]\n"
        "    s=importlib.util.spec_from_file_location('reviewed',root/'reviewed.py')\n"
        "    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        "    child=subprocess.run([sys.executable,'-c',"
        "'import reviewed; print(reviewed.value)'],cwd=root,capture_output=True,text=True)\n"
        "    print(json.dumps({'value':m.value,'child':child.stdout.strip(),"
        "'child_rc':child.returncode,'prefix':sys.pycache_prefix,"
        "'no_writes':sys.dont_write_bytecode}))\n"
        "    return 0\n"
    )
    helper = tmp_path / "reviewed.py"
    helper.write_text("value = 'reviewed-source'\n")
    caches = [
        poison(runtime, tmp_path / "runtime-poison"),
        poison(helper, tmp_path / "helper-poison"),
    ]
    result = subprocess.run(
        [sys.executable, str(wrapper), "pretooluse"],
        cwd=tmp_path,
        env=clean_environment(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "value": "reviewed-source",
        "child": "reviewed-source",
        "child_rc": 0,
        "prefix": os.devnull,
        "no_writes": True,
    }
    assert not (tmp_path / "runtime-poison").exists()
    assert not (tmp_path / "helper-poison").exists()
    for cache, before in caches:
        assert cache.read_bytes() == before


def test_workflow_cli_isolates_imports_and_fixed_helper_children(tmp_path):
    scripts = tmp_path / "scripts"
    shutil.copytree(
        ROOT / "plugins/gas-city-workflow/scripts",
        scripts,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    helper = scripts / "reviewed.py"
    helper.write_text("value = 'reviewed-source'\n")
    context = scripts / "project_context.py"
    observation = tmp_path / "import-observation.json"
    # A fixture-only observation at the end of the real imported module proves
    # the CLI established its policy before project imports, not after argparse.
    context.write_text(
        context.read_text() + "\n" + "import subprocess as _subprocess\n"
        "_child=_subprocess.run([sys.executable,'-c','import reviewed; print(reviewed.value)'],"
        "capture_output=True,text=True)\n"
        f"Path({str(observation)!r}).write_text(json.dumps({{'prefix':sys.pycache_prefix,"
        "'no_writes':sys.dont_write_bytecode,'child':_child.stdout.strip(),"
        "'child_rc':_child.returncode}))\n"
    )
    caches = [
        poison(context, tmp_path / "context-poison"),
        poison(scripts / "_repo_structure.py", tmp_path / "layout-poison"),
        poison(helper, tmp_path / "child-poison"),
    ]
    result = subprocess.run(
        [sys.executable, str(scripts / "workflow.py"), "--help"],
        cwd=scripts,
        env=clean_environment(),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "coordinate" in result.stdout
    assert json.loads(observation.read_text()) == {
        "prefix": os.devnull,
        "no_writes": True,
        "child": "reviewed-source",
        "child_rc": 0,
    }
    assert not (tmp_path / "context-poison").exists()
    assert not (tmp_path / "layout-poison").exists()
    assert not (tmp_path / "child-poison").exists()
    for cache, before in caches:
        assert cache.read_bytes() == before


@pytest.mark.parametrize("disable_writes", [False, True])
def test_negative_controls_really_execute_poisoned_cache(tmp_path, disable_writes):
    source = tmp_path / "reviewed.py"
    source.write_text("value = 'reviewed-source'\n")
    marker = tmp_path / "poisoned"
    cache, before = poison(source, marker)
    prefix = "import sys; sys.dont_write_bytecode=True; " if disable_writes else ""
    result = subprocess.run(
        [sys.executable, "-c", prefix + "import reviewed"],
        cwd=tmp_path,
        env=clean_environment(),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert marker.read_text() == "poison"
    assert "adversarial cache executed" in result.stderr
    assert cache.read_bytes() == before
