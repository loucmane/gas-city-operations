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
    # prep: the r7 and r8 history notes; brief: title, the two history-line mentions, and four task-section ones
    # (continues, do-not-touch twice, checkpoint path); window-base: the S4 TERMINAL record path and its comment.
    allowed = {'prep-r11.py': 3, 'worker-brief.md': 7, 'window-base-r11.py': 2}
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
    assert "        require(RECOVERY is None, 'no recovery admission')\n" \
           "        image = {key: prior[key] for key in ACCEPTED_KEYS}\n" in base
    release = (HERE/'release-r11.py').read_text()
    assert "BASE_COMMIT = '%s'" % BASE in release
    [allowed] = re.findall(r"^ALLOWED = (\{.*\})$", release, re.M)
    allowed = eval(allowed)
    assert len(allowed) == 21 and '.gitignore' in allowed
    for path in allowed - {'.gitignore'}:
        probe = subprocess.run(['git', '--no-optional-locks', '-C', CORE, 'cat-file', '-e', BASE + ':' + path],
                               capture_output=True)
        assert probe.returncode == 0, path


def test_accepted_image_is_the_s4_terminal_record(gen):
    """s2 r2: the accepted image is the S4 TERMINAL observed-after record, whose pinned city.toml and receipt carry
    the window's baseline digests; the provider pins stay the P7 ones. The live comparison itself needs the
    supervisor namespaces (README: the read-only check found the live image equal to it)."""
    base = (HERE/'window-base-r11.py').read_text()
    assert "ACCEPTED = Path('%s')" % gen.ACCEPTED_TERMINAL in base
    assert "ACCEPTED_SHA = '%s'" % gen.ACCEPTED_TERMINAL_SHA in base
    assert sha(gen.ACCEPTED_TERMINAL) == gen.ACCEPTED_TERMINAL_SHA
    record = json.loads(Path(gen.ACCEPTED_TERMINAL).read_bytes())
    assert set(('cache', 'host', 'pins', 'protected')) <= set(record)
    [city0] = re.findall(r"CITY_SHA = \('([0-9a-f]{64})',", base)
    [receipt0] = re.findall(r"RECEIPT_SHA = \('([0-9a-f]{64})',", base)
    assert record['pins']['/home/loucmane/gascity/city/city.toml']['sha256'] == city0
    assert record['pins']['/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json']['sha256'] == receipt0
    provider = '/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json.provider-pins'
    assert "PROVIDER = Path('%s')" % provider in base
    assert "PROVIDER_SHA = '%s'" % sha(provider) in base
    assert "accepted_provider=json.loads(read(PROVIDER,PROVIDER_SHA))" in base
    for name in ('observe-integrity-r11.py', 'window-r11.py'):
        text = (HERE/name).read_text()
        assert 'admitted_against_previous_terminal=True' in text and 'p7_snapshot' not in text, name


def test_prep_overlay_and_wrapper(gen):
    prep = (HERE/'prep-r11.py').read_text()
    overlay = hashlib.sha256(gen.successor_overlay()).hexdigest()
    assert "OVERLAY_SHA = '%s'" % overlay in prep
    assert "WORK = '%s'" % WORK in prep
    assert "ROOT = Path('/var/tmp/ga-n12k-prep-20260925-r1')" in prep
    wrapper = (HERE/'operator'/'PREP.sh').read_text()
    assert re.search(r'^PREP_SHA=([0-9a-f]{64})$', wrapper, re.M).group(1) == sha(HERE/'prep-r11.py')
    assert '# ga-n12k window prep r8:' in wrapper


def test_prep_outputs_are_pinned(gen):
    """s2: each window-base PREP pin is the digest of the ga-n12k PREP output it names and agrees with result.json."""
    root = gen.PREP_ROOT
    result = json.loads((root/'result.json').read_bytes())
    assert result['ok'] is True and result['worker_launched'] is False and result['installed'] is False
    assert result['changed_receipt_fields'] == ['permission_revision', 'receipt_sha256']
    assert result['effective_order_names'] == ['nudge-on-route']
    base = (HERE/'window-base-r11.py').read_text()
    [city] = re.findall(r"CITY_SHA = \('[0-9a-f]{64}',\n +'([0-9a-f]{64})'\)", base)
    [receipt] = re.findall(r"RECEIPT_SHA = \('[0-9a-f]{64}',\n +'([0-9a-f]{64})'\)", base)
    [revision] = re.findall(r"REVISION = \('[0-9a-f]{64}',\n +'([0-9a-f]{64})'\)", base)
    assert city == sha(root/'city.isolated.toml') == result['city_after_sha256']
    assert receipt == sha(root/'receipt.final.json') == result['receipt_after_sha256']
    assert revision == result['revision_after']
    assert "read(PREP/'result.json', '%s')" % sha(root/'result.json') in base
    assert sha(root/'orders.isolated.json') == gen.ORDERS_SHA
    assert "orders = json.loads(read(PREP/'orders.isolated.json', '%s'))" % gen.ORDERS_SHA in base
    for old, _ in gen.PREP_PINS:
        assert old not in base


def test_brief_order_and_commands():
    brief = (HERE/'worker-brief.md').read_text()
    assert "-run '^TestMetadataParentsRefuseUnrelatedEntriesAndHardLinks$/^valid$'" in brief
    assert "-run '^TestMetadataProtectedSiblingParentContract$/^valid$'" in brief
    assert '`/home/loucmane/gascity/bin/bd show ga-n12k --json`' in brief
    assert 'base copy' not in brief and 'Do not create a copy of any source file.' in brief
    task = brief.split('## Worker-owned implementation and tests')[1]
    assert task.index('sha256sum') < task.index('Before any source edit') < task.index('except the two dispatch gate files')


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
