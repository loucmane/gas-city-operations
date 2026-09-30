"""Offline entry-path regression: no launch, service or Git mutation."""
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGNS = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs')
PREFIX = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
spec = importlib.util.spec_from_file_location('entry_review_jobrunner', DESIGNS/'gct-jobrunner/jobrunner.py')
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def test_original_dot_name_is_refused():
    assert J.WRAPPER.fullmatch(PREFIX+'ga-e0t1.20-astra-bootstrap/operator/WORKTREE.sh') is None


def test_corrected_entry_names_are_admissible():
    for name in ('WORKTREE', 'PREP'):
        assert J.WRAPPER.fullmatch(PREFIX+'ga-e0t1-20-astra-entry/operator/'+name+'.sh')


def test_wrappers_are_byte_identical_to_reviewed_sources():
    expected = {'WORKTREE': '44149d6f13757d3605a9579ae6077d2856ae1d0397d4a44c822641ca6833f0b5',
                'PREP': 'ad9e4ee33a50d6b33bc2074a2b2ede214315699b6fb4c4970bf4a318d74e35a0'}
    for name, digest in expected.items():
        actual = (HERE/'operator'/f'{name}.sh').read_bytes()
        assert actual == (DESIGNS/'ga-e0t1.20-astra-bootstrap/operator'/f'{name}.sh').read_bytes()
        assert hashlib.sha256(actual).hexdigest() == digest


def test_successor_job_ids_are_admissible():
    for name in ('worktree', 'prep'):
        assert J.JOB_ID.fullmatch(f'ga-e0t1-20-s1-{name}-r2')
