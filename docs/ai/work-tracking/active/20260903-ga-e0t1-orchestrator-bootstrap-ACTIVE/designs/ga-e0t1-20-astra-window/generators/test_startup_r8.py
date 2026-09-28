"""Fresh uninstalled preparation after the accepted private-creation repair."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import types

import pytest
import startup_r8 as s


def configured():
    ns = dict(__name__='fixture', __file__='fixture.py')
    exec(compile(s.components()['prompt-prep-r8.py'], 'fixture.py', 'exec'), ns)
    return ns['configure']()


def test_probe_is_only_a_fresh_evidence_path():
    out = s.components()
    assert out['worker-startup-r8.py'].replace(b'/r8', b'/r7') == s.frozen('worker-startup-r7.py')
    prompt = out['PRECLAIM-R8.md']
    assert prompt.count(s.sha(out['worker-startup-r8.py']).encode()) == 2
    assert b'worker-startup-r7.py' not in prompt
    assert b'.gc/worker-evidence/ga-e0t1.20/r8/startup.json' in prompt


def test_exact_r7_close_and_permission_receipt_bound():
    out = s.components(); text = out['prompt-prep-r8.py'].decode()
    assert s.CLOSE in text and s.CLOSE_SHA in text
    assert "closed_session='ci-zcoet'" in text and s.CLOSE_EXECUTOR in text
    assert '/ga-e0t1.20-startup-release-20260928-r7' in text
    assert "final['profiles']==before['profiles']" in text
    assert 'helper.config_delta(value,changed,str(PROMPT))' in text
    assert 'runtime.verify_assets(probe.read_regular)' in text
    assert s.sha(out['permissions-baseline-r8.py']) in text
    assert text.count('old._verify_host_assets()') == 2


def test_wrapper_fresh_closed_and_source_pinned():
    out = s.components(); wrapper = out['operator/PROMPT-PREP-R8.sh']
    assert s.sha(out['prompt-prep-r8.py']).encode() in wrapper
    assert s.ROOT.encode() in wrapper
    assert b'COMPLETED OPERATION' not in wrapper
    assert b'PROMPT-PREP-R7B' not in wrapper
    assert subprocess.run(['/bin/sh','-n'], input=wrapper, capture_output=True).returncode == 0


def test_create_only_no_worker_admission(tmp_path):
    root = tmp_path/'out'; s.main(str(root))
    manifest = json.loads((root/'prompt-prep-r8-manifest.json').read_bytes())
    assert not manifest['execution_admitted'] and not manifest['worker_launch_included']
    for name, pin in manifest['files'].items():
        assert s.sha((root/name).read_bytes()) == pin
    with pytest.raises(AssertionError, match='create-only'): s.main(str(root))


def test_host_guard_cannot_be_skipped_on_main():
    tree = ast.parse(s.components()['prompt-prep-r8.py'])
    code = compile(ast.Module(body=[tree.body[-1]],type_ignores=[]), 'entry', 'exec')
    calls=[]
    def guard(): calls.append('host'); raise RuntimeError('permission drift')
    old = types.SimpleNamespace(_SOURCE_SHA='pin', read=lambda *a: b'pin',
        _verify_host_assets=guard, main=lambda: calls.append('main'),
        normalize_main=lambda root: calls.append('normalize'))
    ns=dict(__name__='__main__',__file__='test.py',configure=lambda:old,
        sys=types.SimpleNamespace(argv=['test.py']),Path=Path,ROOT=Path(s.ROOT))
    with pytest.raises(RuntimeError,match='permission drift'): exec(code,ns)
    assert calls == ['host']
    ns['sys'].argv=['test.py','normalize',s.ROOT]; calls.clear(); exec(code,ns)
    assert calls == ['normalize']
    ns['sys'].argv=['test.py','normalize','/tmp/wrong']
    with pytest.raises(AssertionError): exec(code,ns)


def test_result_publication_rechecks_guard(tmp_path):
    old = configured(); old.ROOT=tmp_path
    def guard(): raise RuntimeError('permission drift')
    old._verify_host_assets=guard
    with pytest.raises(RuntimeError,match='permission drift'): old.write('result.json',{'ok':True})
    assert not (tmp_path/'result.json').exists()


def test_permission_guard_exact_and_read_only(monkeypatch):
    import permissions_baseline_r8 as p
    expected=json.loads(Path(p.POSTIMAGE).read_bytes())
    calls=[]; current=json.loads(json.dumps(expected))
    fake=types.SimpleNamespace(open_exact=lambda path, directory=False: calls.append(('open',path,directory)) or path,
        image=lambda fd: current[fd], stable_identity=lambda path,fd: calls.append(('identity',path)))
    monkeypatch.setattr(p.os,'close',lambda fd: calls.append(('close',fd)))
    def read(path,pin):
        raw=Path(path).read_bytes(); assert hashlib.sha256(raw).hexdigest()==pin; return raw
    module=lambda path,pin,name: fake
    p.verify(read,module)
    assert sum(row[0]=='open' for row in calls)==6
    assert sum(row[0]=='close' for row in calls)==6
    for field in ('mode','uid','gid','ino','dev','nlink','size','mtime_ns','ctime_ns'):
        current=json.loads(json.dumps(expected)); target=next(iter(current))
        current[target]['stat'][field] += 1
        with pytest.raises(AssertionError,match='permission postimage'): p.verify(read,module)
    current=json.loads(json.dumps(expected)); current[next(iter(current))]['xattrs']={}
    with pytest.raises(AssertionError,match='permission postimage'): p.verify(read,module)


def test_permission_guard_requires_accepted_result(monkeypatch):
    import permissions_baseline_r8 as p
    def read(path,pin):
        raw=Path(path).read_bytes()
        if str(path)==p.RESULT:
            value=json.loads(raw);value['ok']=False;return json.dumps(value).encode()
        return raw
    with pytest.raises(AssertionError,match='accepted permissions recovery'):
        p.verify(read,lambda *args: pytest.fail('must refuse before metadata read'))
