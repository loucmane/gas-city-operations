"""Tests for the gct-e8ex brief split (read-only: the reviewed r6 brief from git and the recorded live read).

  python3 -m pytest -q designs/gct-e8ex-split/test_split_e8ex.py
"""
import hashlib
import json
import tempfile
import types
from pathlib import Path

import pytest

HERE = Path(__file__).parent
LIVE = HERE.parent.parent / 'reports' / 'gct-e8ex-split-20260926' / 'live-gct-e8ex.json'


def load():
    m = types.ModuleType('split_e8ex'); m.__file__ = str(HERE/'split_e8ex.py')
    exec(compile((HERE/'split_e8ex.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
    return m


@pytest.fixture(scope='module')
def s():
    return load()


@pytest.fixture(scope='module')
def rendered(s):
    with tempfile.TemporaryDirectory() as tmp:
        yield s.render(tmp, 'gct-aaaa', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee', 'gct-ffff')


def test_reassembles_to_the_reviewed_r6_brief(s, rendered):
    full = s.r6()
    task = rendered['task.md']
    head = task[:task.index('## The full specification (read first)')]
    tail = task[task.index('## Out of scope'):]
    bodies = [rendered['spec-%d.md' % n].split('\n\n', 1)[1] for n in range(1, 6)]
    assert head + ''.join(bodies) + tail == full
    assert hashlib.sha256(full.encode()).hexdigest() == s.R6_SHA


def test_the_live_umbrella_description_is_the_reviewed_brief(s):
    """The recorded live read of gct-e8ex (2026-09-26) carries exactly the reviewed r6 brief."""
    bead = json.loads(LIVE.read_text())[0]
    assert bead['id'] == 'gct-e8ex' and bead['status'] == 'open'
    assert hashlib.sha256(bead['description'].encode()).hexdigest() == s.R6_SHA


def test_every_part_is_small(rendered):
    """Plain views run about 1.7 times the text; keep every part under 5000 bytes and 80 lines. The live views
    are measured again after creation, with a hard stop at 9000 bytes or 200 lines (README run order)."""
    for name, text in rendered.items():
        assert len(text.encode()) < 5000 and text.count('\n') < 80, name


def test_pointer_uses_the_codex_prompt_read_command(rendered):
    task = rendered['task.md']
    for n, sid in enumerate(('gct-aaaa', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee', 'gct-ffff'), 1):
        assert '%d. `/home/loucmane/gascity/bin/gc bd show %s`' % (n, sid) in task
    assert 'escalate to the mayor as your prompt describes' in task
    assert task.index('## The full specification') < task.index('## Out of scope') < task.index('## Acceptance')
    assert "does not apply to these six holders" in task and 'Do not close this Bead' in task
    assert '/Docs/worklogs/gct-e8ex-template-candidate-lane.md' in task and 'Do not read, update or close it' in task


def test_guidance_holder_carries_the_review_guidance(s, rendered):
    text = rendered['spec-6.md']
    assert text.startswith('gct-e8ex worker guidance (holder 6 of 6)') and s.GUIDANCE in text
    for needle in ('ReadControlPolicy', 'InspectToolchain', 'run-isolated-composition.py', 'managedworker_test',
                   'gas-city-template-candidate-worktrees'):
        assert needle in text, needle


def test_spec_holders_name_themselves(rendered):
    for n in range(1, 6):
        header = rendered['spec-%d.md' % n].split('\n\n', 1)[0]
        assert header.startswith('gct-e8ex spec part %d of 5' % n) and 'not a work item and is\nclosed' in header
