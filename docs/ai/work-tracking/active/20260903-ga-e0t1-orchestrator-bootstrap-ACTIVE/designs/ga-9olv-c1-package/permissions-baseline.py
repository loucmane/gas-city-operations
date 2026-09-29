"""Read-only continuation of the exact protected history after restored failed ga-x2wz.

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
PRIOR = Path('/tmp/ga-x2wz-permission-capture-20260929-r1')
CAPTURE = Path('/tmp/ga-9olv-permission-capture-20260929-r1')
IMAGES_SHA = '648ae4fb810cbeb85fed0c96d9ad3b2f1bfb69a2a19e0362be8a0d31fc9df44a'
HISTORY_SHA = '3f92c01e415ea74a489475dc0adc36af46a1e8c00b66b831caf3ba59989a93a9'
RESULT_SHA = '03036644c8f48f188ba6eeb49a97656796d01a9ac6c3e369a1b3e8af4b934e1c'
DAY = '/home/loucmane/.codex/sessions/2026/09/29'
TRANSCRIPT = DAY+'/rollout-2026-09-29T14-04-12-01a0ed0d-143b-7700-adf8-debeb7917a3e.jsonl'
TRANSCRIPT_SIZE = 188248
TRANSCRIPT_SHA = 'cd8dada5ad8a14053aebe1c2262b5cd6fd6a225d8e2984edbfff909994e7e34d'


def expected(old, history, images, current):
    assert set(images) == set(old) | {TRANSCRIPT}, 'unexpected image inventory'
    for path, before in old.items():
        actual = copy.deepcopy(images[path])
        if path == DAY:
            assert actual['stat']['mtime_ns'] == actual['stat']['ctime_ns']
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
        json.loads(read(PRIOR/'images.json', '6d9101d8f57cd87f02294f97a21922735f8b1df7c8aa7c6550138f4aa2b4c4e2')),
        json.loads(read(PRIOR/'history.json', '21340fdbc9e372fa9bd04885f9069bdf8641c08da51a6e5f216b4fe6b329a4d1')),
        json.loads(read(CAPTURE/'images.json', IMAGES_SHA)),
        json.loads(read(CAPTURE/'history.json', HISTORY_SHA)))
    capture = json.loads(read(CAPTURE/'result.json', RESULT_SHA))
    assert capture == dict(ok=True, completed_session='ci-di744',
        only_added_path=TRANSCRIPT, only_changed_prior_path=DAY,
        allowed_prior_fields=['mtime_ns', 'ctime_ns'], transcript_size=TRANSCRIPT_SIZE,
        transcript_sha256=TRANSCRIPT_SHA, permissions_changed=False,
        worker_launched=False, historical_entries_preserved=True)
    previous = module(HERE.parent/'ga-x2wz-c1-package/permissions-baseline.py',
        '29b9e38fc676fa1e21a1ef94aa4b310f43bae5f0e268915eeba42a762aad3e15',
        'previous_exact_permission_reader')
    older = module(HERE.parent/'ga-1aa1-image-tool-r3/permissions-baseline.py',
        '971f5ffde5be045624e7df8d0b3b10b3658d5b1d10c9b12e9c3a3fb3e4ccfd45',
        'older_exact_permission_reader')
    entries = {}
    def observe(path, fd):
        if path == TRANSCRIPT:
            return completed_transcript_image(m, fd)
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
