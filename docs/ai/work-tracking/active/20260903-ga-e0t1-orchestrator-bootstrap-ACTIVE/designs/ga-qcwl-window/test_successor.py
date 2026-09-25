"""Tests for the ga-qcwl (ga-e0t1.15 S4) seventh-successor window package.

  python3 -m pytest -q designs/ga-qcwl-window/test_successor.py

Read-only. The anchor tests read the P7 evidence roots, the rebuilt diagnostics and inspector, and the Core rig's
Git objects; nothing is written.
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


def test_kick_and_reconcile_are_dropped():
    names = set(package_files())
    assert not {n for n in names if 'kick' in n.lower() or 'reconcile-predecessor' in n or n.endswith('RECONCILE.sh')}
    assert len([n for n in names if n.startswith('operator/')]) == 34


def test_ga_nibd_survives_only_as_attributed_history(gen):
    for name, raw in package_files().items():
        text = raw.decode()
        for phrase in gen.KEEP:
            text = text.replace(phrase, '')
        allowed = (text.count('the ga-nibd prep on the post-S3 host') + text.count('The overlay is the ga-nibd r6 overlay')
                   + text.count('It is the reviewed ga-nibd prep (the ga-gegx prep)'))
        assert text.count('ga-nibd') == allowed, name


def test_host_epoch_and_image():
    base = (HERE/'window-base-r11.py').read_text()
    assert "('core','2940569','123479699122'), ('signer','2310','39660502')" in base
    assert "('broker','2940285','123477220085')" in base
    assert "return 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'" in base
    assert "o.GC_SHA = b_gc_sha()" in base
    for name in ('window-base-r11.py', 'window-r11.py', 'route-chain-r1.py'):
        text = (HERE/name).read_text()
        assert '2331' not in text and '2940569' in text, name
    assert base.count('2940569') == 3


def test_accepted_anchor_is_the_p7_snapshot():
    base = (HERE/'window-base-r11.py').read_text()
    for path, pin in re.findall(r"(?:ACCEPTED|WITNESS) = Path\('([^']+)'\)\n(?:ACCEPTED|WITNESS)_SHA = '([0-9a-f]{64})'", base):
        assert sha(path) == pin, path
    [provider] = re.findall(r"PROVIDER_SHA = '([0-9a-f]{64})'", base)
    assert sha('/var/tmp/ga-e0t1.15-p7-adoption-20260925/after.json.provider-pins') == provider
    [draft] = re.findall(r"INPUT_SHA = \('([0-9a-f]{64})',", base)
    assert sha('/var/tmp/ga-e0t1.15-p7-input-20260925/receipt.input.draft.json') == draft
    assert "        require(RECOVERY is None, 'no recovery admission in S4')\n        image = prior\n" in base
    assert 'RECOVERY' not in (HERE/'observe-integrity-r11.py').read_text().replace('# S4: no recovery admission', '')


def test_inspector_binding():
    record = json.loads(Path('/var/tmp/ga-e0t1.15-platform-inspector-20260925/build-result.json').read_bytes())
    for name in ('observe-integrity-r11.py', 'observe-terminal-r11.py'):
        text = (HERE/name).read_text()
        assert "BUILD=Path('/var/tmp/ga-e0t1.15-platform-inspector-20260925')" in text
        assert "BINARY_SHA='%s'" % record['binary_sha256'] in text
        assert record['core_commit'] in text and record['core_tree'] in text and record['entrypoint_sha256'] in text
        assert sha('/var/tmp/ga-e0t1.15-platform-inspector-20260925/build-result.json') in text
        assert "MANIFEST_SHA='%s'" % sha('/home/loucmane/gascity/city/.gc/platform/install-manifest.json') in text
    assert "INSPECTOR_SHA='%s'" % record['binary_sha256'] in (HERE/'window-r11.py').read_text()


def test_prep_bindings(gen):
    prep = (HERE/'prep-r11.py').read_text()
    for name, path in (('COMPOSE_SHA', '/var/tmp/ga-e0t1.15-compose-diagnostic-20260925/compose'),
                       ('FINALIZE_SHA', '/var/tmp/ga-e0t1.15-preflight-diagnostic-20260925/compose'),
                       ('PRIOR_SHA', '/var/tmp/ga-e0t1.15-p7-input-20260925/receipt.input.draft.json'),
                       ('RECEIPT_SHA', '/home/loucmane/gascity/city/.gc/runtime/provisioning/receipt.json'),
                       ('CITY_SHA', '/home/loucmane/gascity/city/city.toml')):
        assert "%s = '%s'" % (name, sha(path)) in prep, name
    assert "REVISION = '2113693eefd3a9c905554a294e36ab3b5a17bc63004280b7144ff069ef75acc2'" in prep
    assert "OVERLAY_SHA = '%s'" % hashlib.sha256(gen.successor_overlay()).hexdigest() in prep
    assert "WORK = '/home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins'" in prep


def test_release_admits_exactly_the_ga_qcwl_files(gen):
    text = (HERE/'release-r11.py').read_text()
    assert "BASE_COMMIT = 'b6843d3f539eeebaf9d9c12e7d095d25cdee585d'" in text
    [allowed] = re.findall(r"^ALLOWED = (\{.*\})$", text, re.M)
    assert eval(allowed) == set(gen.ALLOWED)
    for path in gen.ALLOWED:
        if path != '.gitignore':
            probe = subprocess.run(['git', '--no-optional-locks', '-C', CORE, 'cat-file', '-e',
                                    'b6843d3f539eeebaf9d9c12e7d095d25cdee585d:' + path], capture_output=True)
            assert probe.returncode == 0, path


def test_brief(gen):
    brief = (HERE/'worker-brief.md').read_text()
    assert '- Worktree /home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins.' in brief
    assert '- Branch codex/ga-qcwl-provider-pins.' in brief
    assert '- Initial HEAD b6843d3f539eeebaf9d9c12e7d095d25cdee585d.' in brief
    assert '- Initial tree c9f19d215d271a5dda0bce296dc72c32dfc35499.' in brief
    assert "go test ./internal/managedworker -run '^TestGaqcwlCapabilityProbeNoTests$'" in brief
    assert all(path in brief for path in gen.ALLOWED[:-1])
    assert '--bead ga-qcwl' in brief and "--message 'fix: let pinned wrappers of one provider family share a receipt'" in brief
    assert 'cycle' not in brief.split('## Worker-owned implementation and tests')[1].split('## Artifact')[0].lower()


def test_wrapper_digest_pins():
    files = package_files()
    digests = {hashlib.sha256(data).hexdigest(): name for name, data in files.items()}
    for name, raw in files.items():
        if not name.startswith('operator/'):
            continue
        text = raw.decode()
        for var, value in re.findall(r'^([A-Z_]+_SHA)=([0-9a-f]{64})$', text, re.M):
            assert value in digests, (name, var)


def test_inspector_sources_are_the_reviewed_rebind():
    s4 = HERE.parent/'ga-e0t1.15-deploy'/'s4'
    make = load(s4/'make_s4.py', 'make_s4')
    captured = {}
    make.write = lambda name, text: captured.__setitem__(name, text.encode())
    make.inspector()
    assert set(captured) == {'inspector/platform-inspect-main.go', 'inspector/inspector-build-s4.py'}
    for name, data in captured.items():
        assert (s4/name).read_bytes() == data, name
    record = json.loads(Path('/var/tmp/ga-e0t1.15-platform-inspector-20260925/build-result.json').read_bytes())
    assert record['builder_sha256'] == sha(s4/'inspector'/'inspector-build-s4.py')
    assert record['entrypoint_sha256'] == sha(s4/'inspector'/'platform-inspect-main.go')
    assert record['binary_sha256'] == sha('/var/tmp/ga-e0t1.15-platform-inspector-20260925/platform-inspect')


def test_worktree_is_fresh_at_the_base():
    work = '/home/loucmane/gascity-core-worktrees/ga-qcwl-provider-pins'
    if not Path(work).exists():
        pytest.skip('worktree not created yet')
    head = subprocess.run(['git', '--no-optional-locks', '-C', work, 'rev-parse', 'HEAD', 'HEAD^{tree}'],
                          capture_output=True, text=True, check=True).stdout.split()
    assert head == ['b6843d3f539eeebaf9d9c12e7d095d25cdee585d', 'c9f19d215d271a5dda0bce296dc72c32dfc35499']
    status = subprocess.run(['git', '--no-optional-locks', '-C', work, 'status', '--porcelain', '--untracked-files=all'],
                            capture_output=True, text=True, check=True).stdout
    assert status == ''
