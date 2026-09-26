"""Tests for the R4 brief r13 split (read-only: the r12 brief from git and the recorded ga-x7lx window files).

  python3 -m pytest -q designs/ga-4xg9-brief-r13/test_split_r4.py
"""
import hashlib
import json
import tempfile
import types
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def load():
    m = types.ModuleType('split_r4'); m.__file__ = str(HERE/'split_r4.py')
    exec(compile((HERE/'split_r4.py').read_bytes(), m.__file__, 'exec', dont_inherit=True), m.__dict__)
    return m


@pytest.fixture(scope='module')
def s():
    return load()


@pytest.fixture(scope='module')
def rendered(s):
    with tempfile.TemporaryDirectory() as tmp:
        yield s.render(tmp, 'ga-aaaa', 'ga-bbbb')


def test_reassembles_to_the_reviewed_r12_brief(s, rendered):
    full = s.r12()
    task = rendered['task.md']
    head = task[:task.index('## The full specification (read first)')]
    tail = task[task.index('## Working rules'):]
    bodies = [rendered[n].split('\n\n', 1)[1] for n in ('spec-1.md', 'spec-2.md')]
    assert head + ''.join(bodies) + tail == full
    assert hashlib.sha256(full.encode()).hexdigest().startswith('b46fbffe')


def test_every_part_is_readable_inline(rendered):
    for name, text in rendered.items():
        assert len(json.dumps(text)) < 20000, name


def test_pointer_names_the_exempt_bd_path_with_quoted_ids(rendered):
    task = rendered['task.md']
    for sid in ('ga-aaaa', 'ga-bbbb'):
        assert '`/home/loucmane/gascity/bin/bd show "%s" --json`' % sid in task
    assert 'gc.failure_class spec_unreadable' in task
    assert 'as amended by the pre-window clarifications below' in task


def test_clarifications_cover_every_r12_review_item(s, rendered):
    task = rendered['task.md']
    assert s.CLARIFICATIONS in task
    for needle in ('`tracking.py` PostToolUse site is not generic', '`degraded_pretooluse_fallback`',
                   'every other coordination request', 'at 16 MiB', 'at 1 MiB', 'up to five timed gc calls',
                   '300000 ms', 'except for the residual in item 8', '`COMMANDS`\n   frozenset',
                   'any exception from `_profile()`', "the profile's `canonical_root`",
                   'only after\n   the remedy is abandoned',
                   '`workflow.py reconcile-attachment` exists for `depend` intents only',
                   'more than 30 s after it was\n   killed', 'Observed claim delta', 'the acceptance bullet',
                   'window-prepared Bead'):
        assert needle in task, needle
    assert task.index('## Pre-window clarifications') < task.index('## Working rules')


def test_spec_holders_say_the_clarifications_amend_them(rendered):
    for name in ('spec-1.md', 'spec-2.md'):
        header = rendered[name].split('\n\n', 1)[0]
        assert "amended by the task Bead's pre-window clarifications, which win where they differ" in header, name


def test_observed_deltas_match_the_recorded_ga_x7lx_window():
    """Clarification 9 is exactly the live route and claim delta the ga-x7lx window recorded. Evidence-bound:
    it reads the ga-x7lx window roots under /var/tmp, which are not retained forever."""
    route = Path('/var/tmp/ga-x7lx-route-20260926-r1')
    before = json.loads((route/'task-before.json').read_text())
    routed = json.loads((route/'task-after.json').read_text())
    claimed = json.loads(json.loads(Path('/var/tmp/ga-x7lx-watch-20260926T110229Z/task-phase.json').read_text())['stdout'])[0]

    def delta(x, y):
        top = {k for k in set(x) | set(y) if k != 'metadata' and x.get(k) != y.get(k)}
        mx, my = x.get('metadata') or {}, y.get('metadata') or {}
        meta = {k for k in set(mx) | set(my) if mx.get(k) != my.get(k)}
        return top, meta

    assert delta(before, routed) == ({'updated_at'}, {'gc.routed_to'})
    assert delta(routed, claimed) == ({'status', 'assignee', 'started_at', 'updated_at'},
                                      {'gc.session_id', 'gc.session_name', 'gc.work_branch'})
    assert claimed['status'] == 'in_progress'
