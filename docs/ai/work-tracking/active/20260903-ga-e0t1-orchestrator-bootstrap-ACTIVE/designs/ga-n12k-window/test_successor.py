"""Tests for the ga-n12k (ga-qcwl continuation) eighth-successor window package.

  python3 -m pytest -q designs/ga-n12k-window/test_successor.py

Read-only. The anchor tests read the preserved checkpoint, the ga-qcwl PREP overlay, the P7 evidence and the Core
rig's Git objects; nothing is written. Run outside a quiescent window (plain reads of live pinned files).
"""
import hashlib
import json
import re
import subprocess
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
OWN = {'README.md', 'test_successor.py', 'generators/make_successor.py'}
CORE = '/home/loucmane/gascity/city/rigs/gascity'
WORK = '/home/loucmane/gascity-core-worktrees/ga-n12k-provider-pins-finish'
BASE = 'b6843d3f539eeebaf9d9c12e7d095d25cdee585d'
TREE = 'c9f19d215d271a5dda0bce296dc72c32dfc35499'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    module = types.ModuleType(name); module.__file__ = str(path)
    exec(compile(Path(path).read_bytes(), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


@pytest.fixture(scope='module')
def gen():
    return load(HERE/'generators'/'make_successor.py', 'make_successor')


def package_files():
    out = {}
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            rel = path.relative_to(HERE).as_posix()
            if rel not in OWN:
                out[rel] = path.read_bytes()
    return out


def test_generator_reproduces_the_package(gen):
    out = gen.rebind(gen.sources())
    disk = package_files()
    assert set(out) == set(disk)
    for name, data in out.items():
        assert disk[name] == data, name


def test_same_file_set_as_the_s4_window(gen):
    assert set(package_files()) == set(gen.sources())
    assert len([n for n in package_files() if n.startswith('operator/')]) == 34


def test_ga_qcwl_survives_only_as_attributed_history():
    # prep: the r7 and r8 history notes; brief: title, the two history-line mentions, and three task-section ones.
    allowed = {'prep-r11.py': 3, 'worker-brief.md': 6}
    for name, raw in package_files().items():
        assert raw.decode().count('ga-qcwl') == allowed.get(name, 0), name
    brief = (HERE/'worker-brief.md').read_text()
    assert 'never edit, stage in or run\ngit against /home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins' in brief


def test_identity():
    for name, raw in package_files().items():
        text = raw.decode()
        assert 'ga-qcwl-provider-pins' not in text or name == 'worker-brief.md', name
    base = (HERE/'window-base-r11.py').read_text()
    assert "WORK = Path('%s')" % WORK in base
    assert "BASE = '%s'" % BASE in base
    assert "PREP = Path('/var/tmp/ga-n12k-prep-20260925-r1')" in base


def test_unchanged_epoch_image_and_release():
    base = (HERE/'window-base-r11.py').read_text()
    assert "('core','2940569','123479699122'), ('signer','2310','39660502')" in base
    assert "('broker','2940285','123477220085')" in base
    assert "ACCEPTED_SHA = '7e008d9be0abd067270cf43fc1236cab7fab543a7339486f05422bb62002c56d'" in base
    assert "        require(RECOVERY is None, 'no recovery admission in S4')\n        image = prior\n" in base
    release = (HERE/'release-r11.py').read_text()
    assert "BASE_COMMIT = '%s'" % BASE in release
    [allowed] = re.findall(r"^ALLOWED = (\{.*\})$", release, re.M)
    allowed = eval(allowed)
    assert len(allowed) == 21 and '.gitignore' in allowed
    for path in allowed - {'.gitignore'}:
        probe = subprocess.run(['git', '--no-optional-locks', '-C', CORE, 'cat-file', '-e', BASE + ':' + path],
                               capture_output=True)
        assert probe.returncode == 0, path


def test_prep_overlay_and_wrapper(gen):
    prep = (HERE/'prep-r11.py').read_text()
    overlay = hashlib.sha256(gen.successor_overlay()).hexdigest()
    assert "OVERLAY_SHA = '%s'" % overlay in prep
    assert "WORK = '%s'" % WORK in prep
    assert "ROOT = Path('/var/tmp/ga-n12k-prep-20260925-r1')" in prep
    wrapper = (HERE/'operator'/'PREP.sh').read_text()
    assert re.search(r'^PREP_SHA=([0-9a-f]{64})$', wrapper, re.M).group(1) == sha(HERE/'prep-r11.py')
    assert '# ga-n12k window prep r8:' in wrapper


def test_s1_window_pins_still_name_the_ga_qcwl_prep_outputs(gen):
    """s1 leaves the ga-qcwl PREP digests in place under the ga-n12k root, so the window fails closed until s2."""
    base = (HERE/'window-base-r11.py').read_text()
    for digest in ('449346e33f73c1882dfd52e3caa0dfc8066ddfdb6eb4ef6c422603be60e817ac',
                   'c1761144d7ab3b1d557e097902d681325b647324957df56eff4ee8afa77f78eb',
                   '2de85e1eb06c2b4898aa49896d0683bdd22b77597b8402311dcd956850d93348',
                   '9d59a0b4c2c3ce2d12668039559b0b11eb60f45e625a98996185573816744c92'):
        assert digest in base


def test_checkpoint_is_the_preserved_patch(gen):
    assert sha(Path(gen.CHECKPOINT)/'worker-unstaged.patch') == gen.CHECKPOINT_PATCH_SHA
    brief = (HERE/'worker-brief.md').read_text()
    assert gen.CHECKPOINT in brief and gen.CHECKPOINT_PATCH_SHA in brief
    assert '--bead ga-n12k' in brief
    assert "--message 'fix: let pinned wrappers of one provider family share a receipt'" in brief
    assert "go test ./internal/managedworker -run '^TestGan12kCapabilityProbeNoTests$'" in brief


def test_wrapper_digest_pins():
    files = package_files()
    digests = {hashlib.sha256(data).hexdigest() for data in files.values()}
    for name, raw in files.items():
        if name.startswith('operator/'):
            for var, value in re.findall(r'^([A-Z_]+_SHA)=([0-9a-f]{64})$', raw.decode(), re.M):
                assert value in digests, (name, var)


def test_route_binds_the_new_bind_task():
    route = (HERE/'route-task-r5.py').read_text()
    assert "BIND_SHA='%s'" % sha(HERE/'bind-task-r3.py') in route


def test_worktree_is_fresh_at_the_base():
    head = subprocess.run(['git', '--no-optional-locks', '-C', WORK, 'rev-parse', 'HEAD', 'HEAD^{tree}'],
                          capture_output=True, text=True, check=True).stdout.split()
    assert head == [BASE, TREE]
    branch = subprocess.run(['git', '--no-optional-locks', '-C', WORK, 'symbolic-ref', '--short', 'HEAD'],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert branch == 'codex/ga-n12k-provider-pins-finish'
    status = subprocess.run(['git', '--no-optional-locks', '-C', WORK, 'status', '--porcelain', '--untracked-files=all'],
                            capture_output=True, text=True, check=True).stdout
    assert status == ''
