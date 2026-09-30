"""Read-only continuation of the exact protected history after restored failed ga-goo5.

Only the known completed transcript and its parent's two timestamp fields were
added to the capture. No permission repair, history rewrite or general size
limit relaxation is exposed here.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat

HERE = Path(__file__).parent
SOURCE = HERE.parent/'ga-e0t1-20-codex-permissions/permissions.py'
SOURCE_SHA = 'b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442'
PRIOR = Path('/tmp/ga-goo5-permission-capture-20260930-r1')
CAPTURE = Path('/tmp/ga-jcxb-permission-capture-20260930-r1')
IMAGES_SHA = '1c01117e466acc94faa41f764ea6a35a706f28b24ab5781810a900c838587684'
HISTORY_SHA = '38105b8429a71376ba7d0344a3f63328ac4d572ef51da88bbadfdafb652dfa72'
RESULT_SHA = '1888c1b54a3e8464291d79cbb4572578fca716d2c3c3fe15b5e66f96884bed97'
MONTH = '/home/loucmane/.codex/sessions/2026/09'
DAY = MONTH+'/30'
TRANSCRIPT = DAY+'/rollout-2026-09-30T04-06-11-01a0f00f-ee65-7722-abaa-891ed4de4b09.jsonl'
TRANSCRIPT_SIZE = 157587
TRANSCRIPT_SHA = 'bbbd74ef9764a68795edb67ae5e99e297b6f55fcd2f76710d43cfd538ece94fb'


def expected(old, history, images, current):
    assert set(images) == set(old) | {TRANSCRIPT}, 'unexpected image inventory'
    for path, before in old.items():
        actual = copy.deepcopy(images[path])
        if path == DAY:
            assert actual['stat']['mtime_ns'] == actual['stat']['ctime_ns'] == 1790733971479389408
            for key in ('mtime_ns', 'ctime_ns'):
                actual['stat'][key] = before['stat'][key]
        assert actual == before, 'historical permission baseline changed: '+path
    added = images[TRANSCRIPT]
    assert added['sha256'] == TRANSCRIPT_SHA and added['xattrs'] == {}
    s = added['stat']
    assert s['mode'] == 0o100600 and s['uid'] == s['gid'] == 1000
    assert s['size'] == TRANSCRIPT_SIZE and s['nlink'] == 1
    wanted = copy.deepcopy(history)
    assert TRANSCRIPT not in wanted['sessions']
    wanted['sessions'][DAY] = images[DAY]['stat']
    wanted['sessions'][TRANSCRIPT] = s
    assert current == wanted, 'historical inventory changed'
    return images, current


def completed_transcript_image(m, fd):
    """Exact-size exception for ONE known completed transcript, not any reader."""
    before = os.fstat(fd)
    assert before.st_mode == 0o100600 and before.st_uid == before.st_gid == 1000
    assert before.st_size == TRANSCRIPT_SIZE and before.st_nlink == 1
    assert not os.listxattr(fd)
    os.lseek(fd, 0, os.SEEK_SET)
    data = os.read(fd, TRANSCRIPT_SIZE + 1)
    assert len(data) == TRANSCRIPT_SIZE and os.fstat(fd) == before
    assert hashlib.sha256(data).hexdigest() == TRANSCRIPT_SHA
    return dict(stat={k: getattr(before, 'st_'+k) for k in m.FIELDS},
                xattrs={}, sha256=TRANSCRIPT_SHA)


def verify(read, module):
    m = module(SOURCE, SOURCE_SHA, 'x2_permission_reader')
    images, history = expected(
        json.loads(read(PRIOR/'images.json', '719a48e3c841cecc0e6b0d73055b2ce535e1bcfa76629d6a38e413efc37a6b0e')),
        json.loads(read(PRIOR/'history.json', '3aafa560064c18341c49725aabe01fa9dec0588eeb9ec6863616990336a44bc1')),
        json.loads(read(CAPTURE/'images.json', IMAGES_SHA)),
        json.loads(read(CAPTURE/'history.json', HISTORY_SHA)))
    capture = json.loads(read(CAPTURE/'result.json', RESULT_SHA))
    assert capture == dict(ok=True, completed_session='ci-n1xe4',
        only_added_path=TRANSCRIPT, only_changed_prior_path=DAY,
        allowed_prior_fields=['mtime_ns', 'ctime_ns'], transcript_size=TRANSCRIPT_SIZE,
        transcript_sha256=TRANSCRIPT_SHA, permissions_changed=False,
        worker_launched=False, historical_entries_preserved=True)
    latest = module(HERE.parent/'ga-9olv-c1-package/permissions-baseline.py',
        '4428d83183beb88fb1b321b124fb1514c11f7e861afb6cf5c24242e7990e5371',
        'latest_exact_permission_reader')
    previous = module(HERE.parent/'ga-x2wz-c1-package/permissions-baseline.py',
        '29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15',
        'previous_exact_permission_reader')
    older = module(HERE.parent/'ga-1aa1-image-tool-r3/permissions-baseline.py',
        '971f5ffde5be045624e7df8d0b3b10b3658d5b1d10c9b12e9c3a3fb3e4ccfd45',
        'older_exact_permission_reader')
    newest = module(HERE.parent/'ga-rq5n-c1-package/permissions-baseline.py',
        '470b0afc0cca1c55005f716676949e2a96f0dddd912be94fa5f3fd046bf1dc76',
        'newest_exact_permission_reader')
    predecessor = module(HERE.parent/'ga-xyqo-c1-package/permissions-baseline.py',
        '2074e4bf524d6c0e0e182970ac8c197f9734fc726e17029010121672610c0ccd',
        'predecessor_exact_permission_reader')
    last = module(HERE.parent/'ga-5uc9-c1-package/permissions-baseline.py',
        'a1e721390e3c2bcd31790f4bfe40e7b85af0b5df577334bf1ac644e97c395f04',
        'last_exact_permission_reader')
    completed = module(HERE.parent/'ga-goo5-c1-package/permissions-baseline.py',
        'e655c6cb042f7ff44b3e71ae12cc4770eae8452010f2c44e2faf31e0e1280090',
        'completed_exact_permission_reader')
    entries = {}
    def observe(path, fd):
        if path == last.TRANSCRIPT:
            return last.completed_transcript_image(m, fd)
        if path == completed.TRANSCRIPT:
            return completed.completed_transcript_image(m, fd)
        if path == predecessor.TRANSCRIPT:
            return predecessor.completed_transcript_image(m, fd)
        if path == newest.TRANSCRIPT:
            return newest.completed_transcript_image(m, fd)
        if path == TRANSCRIPT:
            return completed_transcript_image(m, fd)
        if path == latest.TRANSCRIPT:
            return latest.completed_transcript_image(m, fd)
        if path == previous.TRANSCRIPT:
            return previous.completed_transcript_image(m, fd)
        if path == older.TRANSCRIPT:
            return older.completed_transcript_image(m, fd)
        return m.image(fd)
    try:
        for path, before in images.items():
            fd = m.open_exact(path, directory=stat.S_ISDIR(before['stat']['mode']))
            entries[path] = fd
            m.stable_identity(path, fd)
            assert observe(path, fd) == before, 'permission postimage drift: '+path
        for key in ('rules', 'sessions'):
            assert m.inventory('/home/loucmane/.codex/'+key) == history[key], 'inventory drift'
        for path, fd in entries.items():
            m.stable_identity(path, fd)
            assert observe(path, fd) == images[path], 'postimage changed during proof'
        for key in ('rules', 'sessions'):
            assert m.inventory('/home/loucmane/.codex/'+key) == history[key], 'inventory race'
    finally:
        for fd in entries.values():
            os.close(fd)
