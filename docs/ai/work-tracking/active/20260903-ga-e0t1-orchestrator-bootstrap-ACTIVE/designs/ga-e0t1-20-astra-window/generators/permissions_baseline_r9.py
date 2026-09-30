"""Read-only exact R8 terminal successor of the accepted permissions baseline.

The only new entry is the proven private ci-sgd80 native transcript. Its exact
parent mtime and ctime are rebound without changing ownership, modes, ACLs,
content, directory identity, historical files or any installed permission.
"""
import copy
import json
import os
from pathlib import Path
import stat

HERE = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs')
SOURCE = HERE/'ga-e0t1-20-codex-permissions/permissions.py'
SOURCE_SHA = 'b560e231944f54533e6dfa7150e791769d3f29996221a4b1e86362f052e0f442'
POSTIMAGE = '/var/tmp/ga-e0t1.20-codex-permissions-20260928-r2/postimage.json'
POSTIMAGE_SHA = '709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010'
RESULT = '/var/tmp/ga-e0t1.20-codex-permissions-20260928-r2/result.json'
RESULT_SHA = 'baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862'
HISTORY = Path('/var/tmp/ga-e0t1.20-codex-permissions-20260928-r2/historical-inventory.json')
HISTORY_SHA = '4ea728c9230a762163f414c76a259770b89d1758a30387cf19aa1a3922fbd48f'
TRANSCRIPT = '/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T23-08-40-01a0e9d9-331e-7943-864b-f638923703d8.jsonl'
TRANSCRIPT_SHA = '606cc6668ac00b1655cb9a648ece40cba296848bc461f78a02b3776d208c9147'
TRANSCRIPT_STAT = {'ctime_ns': 1790629774515067858, 'dev': 2096, 'gid': 1000,
    'ino': 2893514, 'mode': 33152, 'mtime_ns': 1790629774515067858,
    'nlink': 1, 'size': 158893, 'uid': 1000}
TERMINAL = Path('/var/tmp/ga-e0t1.20-terminal-20260928-r8/result.json')
TERMINAL_SHA = 'dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8'


def expected_postimage(prior):
    expected = copy.deepcopy(prior)
    assert len(expected) == 6, 'permission target cardinality'
    row = expected[str(Path(TRANSCRIPT).parent)]['stat']
    assert row['mtime_ns'] == 1790616986573482191 and row['ctime_ns'] == 1790625522659871637
    row.update(mtime_ns=1790629721295077890, ctime_ns=1790629721295077890)
    return expected


def verify(read, module):
    result = json.loads(read(Path(RESULT), RESULT_SHA))
    assert result.get('ok') is True and result.get('worker_release') is False
    assert result.get('historical_transcripts_modified') is False
    assert result.get('creation_proof', {}).get('all_private') is True
    assert result['creation_proof'].get('unchanged_strict_rules_reader_pass') is True
    terminal = json.loads(read(TERMINAL, TERMINAL_SHA))
    assert all(terminal.get(k) is True for k in ('ok', 'actual_host_verified',
        'accepted_restoration_bound', 'terminal_suspension_endpoint_bound'))
    expected = expected_postimage(json.loads(read(Path(POSTIMAGE), POSTIMAGE_SHA)))
    m = module(SOURCE, SOURCE_SHA, 'accepted_permissions_reader')
    history = json.loads(read(HISTORY, HISTORY_SHA))
    expected_history = copy.deepcopy(history)
    for section in ('rules', 'sessions'):
        for path in expected_history[section]:
            if path in expected:
                expected_history[section][path] = expected[path]['stat']
    assert TRANSCRIPT not in expected_history['sessions']
    expected_history['sessions'][TRANSCRIPT] = TRANSCRIPT_STAT
    entries = {}
    try:
        for path, before in expected.items():
            fd = m.open_exact(path, directory=stat.S_ISDIR(before['stat']['mode']))
            entries[path] = fd
            m.stable_identity(path, fd)
            assert m.image(fd) == before, 'permission postimage drift: ' + path
        fd = m.open_exact(TRANSCRIPT)
        entries[TRANSCRIPT] = fd
        assert m.image(fd) == dict(stat=TRANSCRIPT_STAT, xattrs={}, sha256=TRANSCRIPT_SHA)
        for section in ('rules', 'sessions'):
            assert m.inventory('/home/loucmane/.codex/' + section) == expected_history[section], 'historical inventory drift'
        for path, fd in entries.items():
            m.stable_identity(path, fd)
            before = expected.get(path, dict(stat=TRANSCRIPT_STAT, xattrs={}, sha256=TRANSCRIPT_SHA))
            assert m.image(fd) == before, 'permission postimage drift: ' + path
    finally:
        for fd in entries.values():
            os.close(fd)
