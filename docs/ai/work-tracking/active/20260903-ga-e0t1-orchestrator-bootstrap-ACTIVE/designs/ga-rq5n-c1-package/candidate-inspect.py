"""Read-only candidate proof after TERMINAL; never intake or execute worker code."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-rq5n-c1-package')
BASE_SHA = '9b0a613dd0c2c90cb221c3655e2a16a15d67f5be474793761859d3e960639b1c'
COMMON_SHA = 'eedbd17243be6b9e9a80cd2ac87e251fb88e0fce1530f63752d89a77520d4585'
VALIDATOR_SHA = '036c151e31deec85ae2fed9b2b43d5bc61e791f9bfdc3beb2762394eca137628'
TERMINAL_SHA = '40849101f23ed2fa9e5cfb2101c11e2aa571dd7992f7ab739dc81421a086b712'
ROOT = Path('/var/tmp/ga-rq5n-candidate-inspection-20260929-r1')
TERMINAL = Path('/var/tmp/ga-rq5n-terminal-20260929-r1')
CG = HERE.parent/'ga-6utp-activation-r10/candidate_git.py'
CG_SHA = 'd2894e829618ad1fdcb5640b47b99baa3c783173acccb4f7f5918c958823bebe'


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def file_bytes(path, limit=16 << 20):
    """No links, devices, hardlinks, write-shared files, or changing reads."""
    path = Path(path)
    require(path.resolve(strict=True) == path, 'candidate path alias')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOATIME | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 1000
                and before.st_nlink == 1 and not before.st_mode & 0o022
                and before.st_size <= limit, 'candidate file authority or bound')
        chunks, size = [], 0
        while part := os.read(fd, min(65536, limit + 1 - size)):
            chunks.append(part)
            size += len(part)
            require(size <= limit, 'candidate read overflow')
        require(before == os.fstat(fd) and before == path.lstat() and size == before.st_size,
                'candidate file changed during read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def inventory(root, expected):
    require(root.resolve(strict=True) == root, 'evidence root alias')
    out, total = {}, 0
    def visit(directory):
        nonlocal total
        s = directory.lstat()
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == s.st_gid == 1000
                and not s.st_mode & 0o022, 'evidence directory authority')
        names = sorted(directory.iterdir())
        require(len(names) <= 128, 'evidence directory bound')
        for path in names:
            rel = path.relative_to(root).as_posix()
            require(len(path.relative_to(root).parts) <= 8, 'evidence depth bound')
            if stat.S_ISDIR(path.lstat().st_mode):
                visit(path)
            else:
                raw = file_bytes(path)
                total += len(raw)
                require(total <= 64 << 20 and len(out) < 128, 'total evidence bound')
                out[rel] = dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                mode=stat.S_IMODE(path.lstat().st_mode))
        require(directory.lstat() == s and sorted(directory.iterdir()) == names,
                'evidence directory changed')
    visit(root)
    require(set(out) == set(expected), 'Git and filesystem evidence inventory differ')
    return out


def load(path, pin):
    raw = file_bytes(path)
    require(hashlib.sha256(raw).hexdigest() == pin, 'inspector source binding')
    m = types.ModuleType(path.stem)
    m.__file__ = str(path)
    sys.modules[m.__name__] = m
    exec(compile(raw, str(path), 'exec', dont_inherit=True), m.__dict__)
    return m


def inspect(w, b, o, owned, common):
    # Host verification includes zero native sessions; explicit candidate process
    # observation is rechecked by the existing close implementation.
    w.host(o)
    w.require(w.record('restore-pass.json') == dict(ok=True, full_platform_integrity_still_required=True),
              'window restoration is not proven')
    w.verified_lifecycle(terminal=True)
    terminal = json.loads(w.read(TERMINAL/'result.json'))
    w.require(terminal.get('ok') is True and terminal.get('terminal_suspension_endpoint_bound') is True
              and terminal.get('accepted_restoration_bound') is True, 'TERMINAL did not pass')
    intent = json.loads(w.read(TERMINAL/'intent.json'))
    w.require(intent.get('executor_sha256') == TERMINAL_SHA, 'TERMINAL executor binding')
    before = w.record('common-before.json')
    workspace_before=w.record('workspace-before.json')
    observed = common.observe()
    w.require(not common.compare(before, observed), 'common Git changed before candidate inspection')
    close = w.module(HERE/'close-r11.py', '324fcbb239d7da3190ea35342bbb4eb2d85b727b95cfffcc130087cb2cc67bbe')
    w.require(not close.processes(w.WORK), 'candidate worker process remains')
    cg = w.module(CG, CG_SHA)
    admin = cg.verify_linked(w.WORK.parent, common.COMMON, w.WORK, 'ga-rq5n')
    w.require(admin == w.ADMIN, 'candidate admin binding')
    w.ROOT = ROOT
    ROOT.mkdir(mode=0o700)
    w.save('intent.json', dict(source_sha256=_SOURCE_SHA, common_before_sha256=
        w.digest(w.read(Path('/var/tmp/ga-rq5n-window-20260929-r1')/'common-before.json')),
        product_execution=False, intake=False))
    # Reuse reviewed hardened Git grammar, but all subprocesses also receive
    # owned-phase containment rather than cg.git's ordinary subprocess runner.
    def git(git_dir, work_tree, *args, expected=(0,), **unused):
        w.require(git_dir == w.ADMIN and work_tree == w.WORK, 'unexpected Git target')
        name = 'git-'+str(len(list(ROOT.glob('git-*-started.json'))))
        return w.phase(name, w.HARDENED+list(args), b, owned, expected=expected)['stdout'].encode()
    cg.git = git
    cg.no_drivers(admin, w.WORK)
    cg.no_gitlinks(admin, w.WORK, w.BASE)
    w.require(git(admin, w.WORK, 'rev-parse', 'HEAD').decode().strip() == w.BASE, 'candidate HEAD drift')
    w.require(git(admin, w.WORK, 'branch', '--show-current').decode().strip() == w.contract().BRANCH,
              'candidate branch drift')
    raw = git(admin, w.WORK, 'status', '--porcelain=v1', '--ignored', '--untracked-files=all', '-z')
    accepted = w.contract().candidate_status(raw)
    validator=w.module(HERE/'startup-validation.py',VALIDATOR_SHA)
    whole=validator.workspace_image(w.WORK,file_bytes)
    require(whole.get('.codex/hooks.json')==w.contract().RUNTIME_IMAGE['.codex/hooks.json'],
            'candidate generated hook differs')
    validator.workspace_delta(workspace_before,whole,w.contract().RUNTIME_IMAGE,source=accepted['source'],evidence=True)
    for rel, pin in w.contract().RULES.items():
        w.require(w.digest(file_bytes(w.WORK/rel)) == pin
                  and stat.S_IMODE((w.WORK/rel).lstat().st_mode) == 0o644, 'candidate policy drift')
    evidence_root = w.WORK/'.gc/worker-evidence/ga-rq5n/r1'
    prefix = '.gc/worker-evidence/ga-rq5n/r1/'
    evidence = inventory(evidence_root, [p[len(prefix):] for p in accepted['evidence']])
    sources = {rel: dict(sha256=w.digest(file_bytes(w.WORK/rel)),
                         mode=stat.S_IMODE((w.WORK/rel).lstat().st_mode)) for rel in accepted['source']}
    encoder=w.module(HERE/'create-only-patch.py', '813665c1caa01a7ea409c806a29b6e5698a18bebd10291ef246d3e6cce71acb0')
    payload={rel:file_bytes(w.WORK/rel, w.contract().MAX_PRODUCT_BYTES) for rel in accepted['source']}
    require(all(w.digest(raw)==sources[rel]['sha256'] for rel,raw in payload.items()), 'new file read drift')
    patch=encoder.encode(payload,w.contract().SOURCE_MODES,w.contract().MAX_PRODUCT_BYTES)
    w.require(0 < len(patch) <= 4 << 20, 'candidate patch bound')
    w.durable(ROOT/'candidate.patch', patch)
    w.require(raw == git(admin, w.WORK, 'status', '--porcelain=v1', '--ignored', '--untracked-files=all', '-z'),
              'candidate changed during inspection')
    w.require(evidence == inventory(evidence_root, [p[len(prefix):] for p in accepted['evidence']])
              and all(w.digest(file_bytes(w.WORK/rel)) == row['sha256']
                      and stat.S_IMODE((w.WORK/rel).lstat().st_mode) == row['mode']
                      for rel, row in sources.items()),
              'candidate evidence or source changed')
    w.require(whole==validator.workspace_image(w.WORK,file_bytes),'candidate workspace changed during inspection')
    w.host(o)
    w.require(not close.processes(w.WORK), 'candidate process appeared')
    after = common.observe()
    w.save('common-after.json', after)
    w.require(not common.compare(before, after), 'common Git changed during candidate inspection')
    w.complete_containment()
    w.save('result.json', dict(ok=True, source=sources, evidence=evidence,
        candidate_patch_sha256=w.digest(patch), common_git_unchanged=True,
        candidate_only=True, product_execution=False, intake=False, worker_launched=False))


def main():
    require(globals().get('_SOURCE_SHA') and os.getuid() == os.geteuid() == 1000, 'bound user invocation')
    require(hashlib.sha256(file_bytes(Path(__file__))).hexdigest() == _SOURCE_SHA, 'executor source drift')
    w = load(HERE/'window-base.py', BASE_SHA)
    common = load(HERE/'common-snapshot-r1.py', COMMON_SHA)
    b, o, owned = w.load_support()
    require(not os.path.lexists(ROOT), 'inspection root consumed')
    inspect(w, b, o, owned, common)
    print(json.dumps(dict(ok=True, root=str(ROOT), intake=False)))


if __name__ == '__main__':
    main()
