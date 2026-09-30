"""Pure assembly of fresh BIND/ROUTE operations from the proven R11 controls.

No file writes, subprocesses, routing or launch. The complete window assembler
must supply its exact helper digests before these bytes can be materialized,
signed and independently reviewed. A generated script is not execution authority.
"""
import ast
import hashlib
import re

OLD_BIND = 'fd47b2e632f4573ec3831be4120547315f62edbcbd43aa172eee100396390ac5'
OLD_ROUTE = '6bc45af2ca8d33f35ca5c05c544beb9a007b4d35e22f852896ac77fde8939647'
OLD_BASE = '746e3dcdea4412380dc8d7e5f1b622f4637ad05d26605e19bbedee6e71e000d0'
OLD_WINDOW = '342f90b4b15f455491cb42e420f885ecca946191a1570cb667e813d3dc794e98'
OLD_WORKTREE = '9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af'
WORKTREE = '163cfd690bcd1f0ca7586d3f1f8bad12f49a8a2a7fb5bb8d48175c5b0acf354c'
OLD_DESCRIPTION = '136f2b728a6713c123dab4a79a6fb34934e578bf01cf57658603afdb46166955'
BASE = '801a5a9d5b0d72f665c949a86573357f02c9f1ac'
ROOT = '/var/tmp/ga-rq5n-bind-20260929-r1'
ROUTE = '/var/tmp/ga-rq5n-route-20260929-r1'
PACKAGE = 'ga-rq5n-c1-package'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError('exact source SHA256 required')
    return value


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('assembly anchor missing or ambiguous: ' + before[:80])
    return text.replace(before, after)


def function(text, name, replacement):
    found = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        raise ValueError('function anchor')
    [node] = found
    lines = text.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1]) + replacement.rstrip() + '\n' + ''.join(lines[node.end_lineno:])


def retarget(text):
    text = text.replace('ga-e0t1-20-astra-window', PACKAGE)
    for before, after in (
        ('/var/tmp/ga-e0t1.20-bind-20260927-r1', ROOT),
        ('/var/tmp/ga-e0t1.20-route-20260927-r1', ROUTE),
        ('/var/tmp/ga-e0t1.20-worktree-20260927-r1', '/var/tmp/ga-rq5n-worktree-20260929-r1'),
        ('codex/ga-e0t1.20-c1-close-admission', 'codex/ga-rq5n-c1-package'),
        ('ga-e0t1.20', 'ga-rq5n'),
        ('window-base-r11.py', 'window-base.py'),
        ('window-r11.py', 'window.py'),
    ):
        text = text.replace(before, after)
    return text


def binding(raw, *, base_sha, contract):
    if sha(raw) != OLD_BIND:
        raise ValueError('BIND predecessor differs')
    text = retarget(raw.decode())
    text = once(text, OLD_BASE, pin(base_sha))
    if text.count(OLD_WORKTREE) != 2:
        raise ValueError('WORKTREE receipt anchors')
    text = text.replace(OLD_WORKTREE, WORKTREE)
    text = once(text, OLD_DESCRIPTION, contract.DESCRIPTION)
    text = once(text, '    note=w.contract().BOUND_NOTE', '    note=w.contract().BIND_NOTE')
    text = once(text, "    assert after['notes']==note",
                "    assert after['notes']==w.contract().BOUND_NOTE")
    start = text.index('    for key in set(before)|set(after):')
    end = text.index('    assert w.host(o)==before_host', start)
    text = text[:start] + '    w.contract().validate_binding_delta(before,after)\n' + text[end:]
    text = text.replace('existing nonblocking parent edge', 'existing informational relation')
    ast.parse(text)
    return text.encode()


COMPLETED_BINDING = """def completed_binding(w):
    s=BIND.lstat()
    assert stat.S_ISDIR(s.st_mode) and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o700,'bind root authority'
    intent=json.loads(w.read(BIND/'binding-intent.json'))
    assert set(intent)=={'before','metadata','description_sha256','executor_sha256','worker_launched','note'},'bind intent fields'
    assert intent['executor_sha256']==BIND_SHA and intent['description_sha256']==DESCRIPTION_SHA
    assert intent['worker_launched'] is False and intent['note']==w.contract().BIND_NOTE
    assert intent['metadata']=={'gc.work_dir':str(w.WORK)}
    result=json.loads(w.read(BIND/'result.json'))
    assert result==dict(ok=True,bead='ga-rq5n',contract_bound=True,routed=False,assigned=False,
        worker_launched=False,live_configuration_changed=False)
    before=json.loads(w.read(BIND/'task-before.json'))
    bound=json.loads(w.read(BIND/'task-after.json'))
    assert before==intent['before'],'binding preimage differs'
    w.contract().validate_binding_delta(before,bound)
    return bound
"""


def routing(raw, *, window_sha, binding_sha, contract):
    if sha(raw) != OLD_ROUTE:
        raise ValueError('ROUTE predecessor differs')
    text = retarget(raw.decode())
    text = once(text, OLD_WINDOW, pin(window_sha))
    text = once(text, '9fd6c49adecf7fb991f9b8cd2c6279c25fcf73455bfa0911609a2079928495e7',
                pin(binding_sha))
    text = once(text, OLD_DESCRIPTION, contract.DESCRIPTION)
    text = function(text, 'completed_binding', COMPLETED_BINDING)
    # Preserve supported dry run and one real raw route. Freeze the exact new
    # routed image for startup/close; do not substitute a preflight bound image.
    text = once(text, "    assert after['metadata']==dict(before['metadata'],**{'gc.routed_to':TARGET})",
                "    w.contract().validate_route_delta(before,after)")
    start = text.index('    for key in set(before)|set(after):')
    end = text.index('    assert w.host(o)==before_host', start)
    text = text[:start] + text[end:]
    text = text.replace("variant='template-root-pieces'", "variant='candidate-root-pieces'")
    ast.parse(text)
    return text.encode()


def binding_receipt_reference():
    return ROUTE + '/task-after.json'
