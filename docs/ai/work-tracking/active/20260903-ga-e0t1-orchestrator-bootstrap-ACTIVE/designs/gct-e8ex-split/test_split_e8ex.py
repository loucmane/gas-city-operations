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
        yield s.render(tmp, 'gct-tttt', 'gct-aaaa', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee', 'gct-ffff')


def test_reassembles_to_the_reviewed_r6_brief(s, rendered):
    full = s.r6()
    task = rendered['task.md']
    head = task[:task.index('## Stop check (before anything else)')]
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
    # 9000 / 1.7 is about 5290: the 5000-byte cap leaves little headroom, and the live measurement decides.


def test_pointer_uses_the_codex_prompt_read_command(rendered):
    task = rendered['task.md']
    for n, sid in enumerate(('gct-aaaa', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee', 'gct-ffff'), 1):
        assert '%d. `/home/loucmane/gascity/bin/gc bd show %s`' % (n, sid) in task
    assert 'the mayor as your prompt describes' in task
    assert task.index('## The full specification') < task.index('## Out of scope') < task.index('## Acceptance')
    assert "does not apply to these six holders" in task and 'Holder 6 holds the coordinator notes, binding' in task


def test_notes_holder_carries_the_notes_and_the_review_guidance(s, rendered):
    text = rendered['spec-6.md']
    header = text.split('\n\n', 1)[0]
    assert header.startswith('gct-e8ex coordinator notes and review hints (holder 6 of 6)')
    assert 'not a work item\nand is closed' in header and s.GUIDANCE in text
    for needle in ('"this Bead" means the claimed task, gct-tttt', 'do not read, update or close it',
                   '/Docs/worklogs/gct-tttt.md` (one note per Bead)', 'run `git write-tree` as its own',
                   '`READY FOR SIGNING: gct-tttt tree <digest>`', 'do not run `gc runtime drain-ack`',
                   '`-A`, `.` or `-f`', '`.agents/`, `.claude/skills/` or `.gc/`', '`ESCALATED:` with its reason, then send it', 'stop without sending', 'Keep every task note to a few lines', 'a bounded test summary',
                   '`git diff --cached --name-only`', '`git restore --staged <file>`',
                   'explicit file paths, never a directory', 'refused as ignored is reported',
                   'every test you can run passes', '"The worker\n  report" means',
                   "are the\n  coordinator's"):
        assert needle in text, needle
    for needle in ('ReadControlPolicy', 'InspectToolchain', 'run-isolated-composition.py', 'managedworker_test',
                   'gas-city-template-candidate-worktrees'):
        assert needle in text, needle


def test_render_refuses_bad_ids(s, tmp_path):
    good = ['gct-t1', 'gct-a1', 'gct-b1', 'gct-c1', 'gct-d1', 'gct-e1', 'gct-f1']
    for bad in (good[:6], ['<task>'] + good[1:], ['gct-e8ex'] + good[1:], good[:6] + ['gct-a1'],
                good[:6] + ['gct-x `rm`'], ['gct-e8ex.1'] + good[1:], good[:6] + ['gct-e8ex.2']):
        with pytest.raises(ValueError):
            s.render(tmp_path / 'x', *bad)


def test_spec_holders_name_themselves(rendered):
    for n in range(1, 6):
        header = rendered['spec-%d.md' % n].split('\n\n', 1)[0]
        assert header.startswith('gct-e8ex spec part %d of 5' % n) and 'not a work item and is\nclosed' in header


def test_holders_depend_only_on_the_task_id(s, tmp_path, rendered):
    """r5 (r4 review B must_fix 1): the six holders are rendered from the real task id alone, before their own
    ids exist, and equal the combined render; holder 6 carries no placeholder."""
    alone = s.render_holders(tmp_path / 'h', 'gct-tttt')
    assert sorted(alone) == ['spec-%d.md' % n for n in range(1, 7)]
    for name, text in alone.items():
        assert text == rendered[name], name
    # Only the two intended angle-bracket tokens remain: the digest to fill in and Core's quoted error text.
    assert '<' not in alone['spec-6.md'].replace('<digest>', '').replace('<name>', '').replace('<file>', '')
    assert '<' not in rendered['task.md'][rendered['task.md'].index('## Stop check'):].replace('<n>', '')
    other = s.holders('gct-tttt')
    assert other == alone
    task_only = s.render_task(tmp_path / 't', 'gct-tttt', 'gct-aaaa', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee',
                              'gct-ffff')
    with pytest.raises(ValueError):
        s.render_task(tmp_path / 'u', 'gct-tttt', 'gct-tttt', 'gct-bbbb', 'gct-cccc', 'gct-dddd', 'gct-eeee', 'gct-ffff')
    assert task_only['task.md'] == rendered['task.md']
    for bad in ('<task>', 'gct-e8ex', 'gct-e8ex.3'):
        with pytest.raises(ValueError):
            s.render_holders(tmp_path / 'x', bad)


def test_stop_check_comes_before_every_read(rendered):
    """r7 (r6 review B must_fix 1): the stop check is in the task description itself, before the numbered reads,
    so a restarted session stops before any holder read can fail again."""
    task = rendered['task.md']
    stop = task.index('## Stop check (before anything else)')
    assert stop < task.index('## The full specification (read first)') < task.index('1. `/home/loucmane/gascity/bin/gc bd show')
    head = task[stop:task.index('## The full specification (read first)')]
    for needle in ('`READY FOR SIGNING:`, `ESCALATED:` or `STOPPED:`', 'records an escalation or a failed read',
                   'do not close this Bead, do not run `gc runtime drain-ack`', '`STOPPED: task view truncated`'):
        assert needle in head, needle
    failed = task[task.index('If any read is truncated or fails'):]
    assert failed.index('`ESCALATED: read <n> failed`') < failed.index('then escalate') < failed.index(
        'stop without sending')


def test_ready_note_comes_before_the_mail(rendered):
    """r8 (r7 review A 4): the READY line is appended before the one escalation is sent."""
    text = rendered['spec-6.md']
    assert text.index('`READY FOR SIGNING: gct-tttt tree <digest>`') < text.index('Then send one escalation')
