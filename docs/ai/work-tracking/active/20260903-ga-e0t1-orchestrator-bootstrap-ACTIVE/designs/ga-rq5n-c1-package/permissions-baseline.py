"""Read-only continuation of the exact protected history after restored held ga-9olv.

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
PRIOR = Path('/tmp/ga-9olv-permission-capture-20260929-r1')
CAPTURE = Path('/tmp/ga-rq5n-permission-capture-20260929-r1')
IMAGES_SHA = '552541d28a51845647464f5ab1124a9bdf394b9bcf459309af8cef2522880088'
HISTORY_SHA = 'ea98247158d6306ed1734728ef7bddc8460a5f55494282018281edc89c6d3f88'
RESULT_SHA = '504525a68c4d89632a8ce33b33408ee120d43659b775dee798aab41464b22ac0'
DAY = '/home/loucmane/.codex/sessions/2026/09/29'
TRANSCRIPT = DAY+'/rollout-2026-09-29T16-03-56-01a0ed7a-b36a-7ca2-9499-604faba0a160.jsonl'
TRANSCRIPT_SIZE = 4491142
TRANSCRIPT_SHA = '13341d3d82da0f0318367dab410c31c8e20ecf7bb209202c1fbf0c4fbc3e2b8c'


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
        json.loads(read(PRIOR/'images.json', '648ae4fb810cbeb85fed0c96d9ad3b2f1bfb69a2a19e0362be8a0d31fc9df44a')),
        json.loads(read(PRIOR/'history.json', '3f92c01e415ea74a489475dc0adc36af46a1e8c00b66b831caf3ba59989a93a9')),
        json.loads(read(CAPTURE/'images.json', IMAGES_SHA)),
        json.loads(read(CAPTURE/'history.json', HISTORY_SHA)))
    capture = json.loads(read(CAPTURE/'result.json', RESULT_SHA))
    assert capture == dict(ok=True, completed_session='ci-0xi2z',
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
    entries = {}
    def observe(path, fd):
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
