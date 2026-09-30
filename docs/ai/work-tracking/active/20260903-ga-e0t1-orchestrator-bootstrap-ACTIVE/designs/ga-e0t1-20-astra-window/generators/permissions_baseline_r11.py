"""Exact read-only permission continuation after R10; not a permission grant."""
import copy
import json
import os
from pathlib import Path
import stat
HERE=Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs')
SOURCE=HERE/'ga-e0t1-20-codex-permissions/permissions.py'
SOURCE_SHA='b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442'
CAPTURE=Path('/tmp/ga-e0t1-r11-permission-capture-20260929')
PRIOR=Path('/tmp/ga-e0t1-r10-permission-capture-20260929')
DAY='/home/loucmane/.codex/sessions/2026/09/29'
TRANSCRIPT=DAY+'/rollout-2026-09-29T02-37-25-01a0ea98-50a3-77c1-85ad-7a38c23d40f2.jsonl'
TRANSCRIPT_SHA='7368ea8e311109d97e479ab7308ea8dd9ccec11b85ca860c0fb761c0cf71ab0d'
IMAGES_SHA='2f08cb921d323435855741543ba1a5d53625f4f5e9e0bb14d822c7a4e1044106'
HISTORY_SHA='277e0cdfd212de397deb0aac11c0757343f05ffdba9e55d91a2f3d22675a7653'
POSTIMAGE_SHA='709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010'
RESULT_SHA='baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862'
def expected(old,history,images,current):
    assert set(images)==set(old)|{TRANSCRIPT}
    for p,before in old.items():
        actual=copy.deepcopy(images[p])
        if p==DAY:
            assert actual['stat']['mtime_ns']==actual['stat']['ctime_ns']
            for k in ('mtime_ns','ctime_ns'):actual['stat'][k]=before['stat'][k]
        assert actual==before,'historical permission baseline changed: '+p
    assert images[TRANSCRIPT]['sha256']==TRANSCRIPT_SHA and images[TRANSCRIPT]['xattrs']=={}
    assert images[TRANSCRIPT]['stat']['mode']==0o100600
    assert images[TRANSCRIPT]['stat']['uid']==images[TRANSCRIPT]['stat']['gid']==1000
    expected=copy.deepcopy(history);assert TRANSCRIPT not in expected['sessions']
    expected['sessions'][DAY]=images[DAY]['stat'];expected['sessions'][TRANSCRIPT]=images[TRANSCRIPT]['stat']
    assert current==expected,'historical inventory changed'
    return images,current
def verify(read,module):
    m=module(SOURCE,SOURCE_SHA,'accepted_permission_reader')
    images,history=expected(
        json.loads(read(PRIOR/'images.json','59521dd6056d3d67ca60f87f1b42cea4ce9e9ec4b9648188c742358211c66b48')),
        json.loads(read(PRIOR/'history.json','31b1af6ba05b6baaaf97d049ebd9f59b63d5353558ba869bce012c786965f14d')),
        json.loads(read(CAPTURE/'images.json',IMAGES_SHA)),json.loads(read(CAPTURE/'history.json',HISTORY_SHA)))
    terminal=json.loads(read(Path('/var/tmp/ga-e0t1.20-terminal-20260929-r10/result.json'),
        'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'))
    assert all(terminal.get(k) is True for k in ('ok','actual_host_verified','accepted_restoration_bound','terminal_suspension_endpoint_bound'))
    entries={}
    try:
        for p,before in images.items():
            fd=m.open_exact(p,directory=stat.S_ISDIR(before['stat']['mode']));entries[p]=fd
            m.stable_identity(p,fd);assert m.image(fd)==before,'exact permission postimage drift: '+p
        for k in ('rules','sessions'):assert m.inventory('/home/loucmane/.codex/'+k)==history[k],'historical inventory drift'
        for p,fd in entries.items():m.stable_identity(p,fd);assert m.image(fd)==images[p],'postimage changed during proof'
    finally:
        for fd in entries.values():os.close(fd)
