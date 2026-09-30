"""Offline preparation-only regression tests; no job/lifecycle execution."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import types

import pytest

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'ga-jcxb-c1-package'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def module():
    m = types.ModuleType('fresh_workspace')
    m.__file__ = str(HERE/'worktree.py')
    exec(compile((HERE/'worktree.py').read_bytes(), m.__file__, 'exec'), m.__dict__)
    return m

def test_exact_source_rebinding():
    manifest = json.loads((HERE/'WORKTREE-REBINDING.json').read_bytes())
    for name, digest in manifest['predecessor_sources'].items():
        assert sha((OLD/name).read_bytes()) == digest
    for name, digest in manifest['files'].items():
        assert sha((HERE/name).read_bytes()) == digest
    assert (HERE/'worktree.py').read_bytes() == (OLD/'worktree.py').read_bytes().replace(b'ga-jcxb', b'ga-mb91')
    expected = (OLD/'operator/WORKTREE.sh').read_bytes().replace(b'ga-jcxb', b'ga-mb91').replace(
        manifest['predecessor_sources']['worktree.py'].encode(), manifest['files']['worktree.py'].encode())
    assert (HERE/'operator/WORKTREE.sh').read_bytes() == expected
    assert subprocess.run(['/bin/sh', '-n', str(HERE/'operator/WORKTREE.sh')], capture_output=True).returncode == 0

def test_rules_and_base_unchanged():
    m = module()
    assert m.BASE == '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
    assert m.BRANCH == 'codex/ga-mb91-c1-package'
    assert m.WORK == Path('/home/loucmane/gas-city-ops-candidate-worktrees/ga-mb91')
    assert m.ADMIN == Path('/home/loucmane/gas-city-ops/.git/worktrees/ga-mb91')
    assert m.ROOT == Path('/var/tmp/ga-mb91-worktree-20260930-r1')
    assert (HERE/'inputs.json').read_bytes() == (OLD/'inputs.json').read_bytes()
    data = json.loads((HERE/'inputs.json').read_bytes())
    assert set(data) == {'window-restrictions.rules'}
    raw = base64.b64decode(data['window-restrictions.rules'], validate=True)
    assert sha(raw) == m.RESTRICTION_SHA
    expressions = ast.parse(raw).body
    assert len(expressions) == 7
    assert all(next(k.value.value for k in n.value.keywords if k.arg == 'decision') == 'forbidden'
               for n in expressions)

@pytest.mark.parametrize('entry', [b'160000 commit abc\tmodule\0', b'100644 blob abc\t.gitattributes\0',
    b'100644 blob abc\tnested/.gitattributes\0', b'100644 blob abc\t.gitmodules\0',
    b'100644 blob abc\t.codex/rules/extra.rules\0'])
def test_unsafe_tree_refuses(entry):
    with pytest.raises(AssertionError): module().source_tree(entry)

def test_ordinary_tree():
    module().source_tree(b'100644 blob abc\tfile.py\0')

def test_noatime_and_digest(tmp_path):
    p = tmp_path/'input'
    p.write_bytes(b'immutable')
    before = p.stat().st_atime_ns
    assert module().read(p, sha(b'immutable')) == b'immutable'
    assert p.stat().st_atime_ns == before
    with pytest.raises(AssertionError): module().read(p, '0'*64)

def test_symlink_refuses(tmp_path):
    p = tmp_path/'input'
    p.write_bytes(b'x')
    link = tmp_path/'link'
    link.symlink_to(p)
    with pytest.raises(OSError): module().read(link, sha(b'x'))

def test_exclusive_evidence(tmp_path):
    p = tmp_path/'evidence.json'
    module().write(p, {'ok': True})
    before = p.read_bytes()
    with pytest.raises(FileExistsError): module().write(p, {'ok': False})
    assert p.read_bytes() == before

def test_missing_source_launcher_refuses(monkeypatch):
    m = module()
    monkeypatch.setattr(m, 'read', lambda *a: pytest.fail('read before source marker'))
    with pytest.raises(AssertionError): m.main()

def test_ledger_is_native_standalone():
    b = json.loads((HERE/'LEDGER-BINDING.json').read_bytes())
    assert b['id'] == 'ga-mb91' and b['status'] == 'open'
    assert not b.get('assignee') and not b.get('metadata') and not b.get('parent')
    assert b['dependencies'] == [{'id': 'ga-e0t1', 'dependency_type': 'relates-to'}]

def test_no_worker_or_partial_source_execution():
    text = (HERE/'worktree.py').read_text()
    for forbidden in ('ga-xyqo', 'gct-oak5-c1-window', "'sling'", "'resume'", "'claim'"):
        assert forbidden not in text

def test_latch_exact_previous_terminal_only():
    text = (HERE/'preserve-predecessor-halt.py').read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign)
                and any(getattr(t, 'id', '') == 'JOB_COMMITS' for t in n.targets))
    assert ast.literal_eval(node.value) == {'ga-jcxb-terminal-r1': '4c4c4810ca1cfc87ab08453c1244cb121a03f7d9'}
    for guard in ("assert job in JOB_COMMITS", "done['exit']==EXPECTED_EXIT", "done['unit_state_after']=='inactive'",
                  "blob==Path(__file__).read_bytes()", "rename(directory,b'HALTED',directory,archive.encode(),1)"):
        assert guard in text
    assert '.unlink(' not in text and 'os.unlink' not in text
