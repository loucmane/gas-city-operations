"""Read-only prelaunch check of the accepted six-object permissions postimage.

This exact comparison is for quiescent preparation and prelaunch only. A live
worker creates a new transcript and changes its parent directory metadata, so
postlaunch validation must use the strict transcript reader, not this preimage.
"""
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


def verify(read, module):
    result = json.loads(read(Path(RESULT), RESULT_SHA))
    assert result.get('ok') is True and result.get('worker_release') is False, 'accepted permissions recovery'
    assert result.get('historical_transcripts_modified') is False, 'historical preservation'
    assert result.get('creation_proof', {}).get('all_private') is True, 'private creation proof'
    assert result['creation_proof'].get('unchanged_strict_rules_reader_pass') is True, 'strict rules proof'
    expected = json.loads(read(Path(POSTIMAGE), POSTIMAGE_SHA))
    assert len(expected) == 6, 'permission target cardinality'
    m = module(SOURCE, SOURCE_SHA, 'accepted_permissions_reader')
    entries = {}
    try:
        for path, before in expected.items():
            fd = m.open_exact(path, directory=stat.S_ISDIR(before['stat']['mode']))
            entries[path] = fd
            m.stable_identity(path, fd)
            assert m.image(fd) == before, 'permission postimage drift: ' + path
        # Check the complete held set again, including ancestor identity.
        for path, fd in entries.items():
            m.stable_identity(path, fd)
            assert m.image(fd) == expected[path], 'permission postimage drift: ' + path
    finally:
        for fd in entries.values():
            os.close(fd)
