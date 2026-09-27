"""Pure admission rules for the ga-e0t1.20 operational window.

This is not a launch command, provisioning receipt, or worker source repair.
The full raw Bead and runtime observations remain evidence at each caller.
"""
import hashlib

TASK = 'ga-e0t1.20'
PARENT = 'ga-e0t1'
TARGET = 'gascity/codex'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
BASE = 'c6b789bbe6ff677dd04336803dbf2c2e017812ba'
BRANCH = 'codex/ga-e0t1.20-c1-close-admission'
DESCRIPTION = '136f2b728a6713c123dab4a79a6fb34934e578bf01cf57658603afdb46166955'
ACCEPTANCE = '5cccba5095be80005ea0923e517ff0e1cde570a0613d3e2649ca81eecd315384'
RULES = {
    '.codex/rules/gas-city-native-control.rules': '0a2c32485d71ef31875010ea810deffb0f2936e8c89bb5da2f7f2aeed5044123',
    '.codex/rules/window-restrictions.rules': 'ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773',
}
DEFAULT_RULES = '3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516'
SCOPE_ROOT = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/'
SOURCE_PATHS = tuple(SCOPE_ROOT + path for path in ('DESIGN.md', 'slots/slots.py', 'slots/test_slots.py'))
BOUND_NOTE = 'Operational startup contract for ga-e0t1.20: read /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/WORKER-BRIEF.md sha256 326677a5929eb49a31ca44f42214137266e592e41804d143b2b1f40d9ea9553d. Verify and run /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/worker-startup.py sha256 7c97d1fcfae3b87ddf76a54a449c34232befb0096b77efde07eb8758b6382de3 inside the actual worker sandbox with its real session ID. No product edit until the coordinator verifies startup and releases that exact session. No staging signing task close restart or delegation. Return an uncommitted candidate only.'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def validate_task(value, phase):
    """Validate own fields and the exact known nonblocking edge, never its history.

    The API embeds the parent's changing historical notes in dependencies. They
    are preserved verbatim by the caller, but are neither this worker's brief
    nor its ownership. Same-call before/after mutation comparison stays exact.
    """
    require(phase in ('unbound', 'bound', 'routed'), 'task phase')
    require(value.get('id') == TASK and value.get('parent') == PARENT, 'task identity')
    require(value.get('status') == 'open' and not value.get('assignee'), 'task is owned or terminal')
    require((value.get('notes') or '') == ('' if phase == 'unbound' else BOUND_NOTE)
            and value.get('comment_count', 0) == 0, 'unexpected task notes')
    require(value.get('issue_type') == 'task' and value.get('priority') == 2, 'task type or priority')
    for name, digest in (('description', DESCRIPTION), ('acceptance_criteria', ACCEPTANCE)):
        text = value.get(name)
        require(isinstance(text, str) and hashlib.sha256(text.encode()).hexdigest() == digest,
                'task contract drift: ' + name)
    deps = value.get('dependencies')
    require(isinstance(deps, list) and len(deps) == 1 and isinstance(deps[0], dict), 'dependency cardinality')
    require((deps[0].get('id'), deps[0].get('dependency_type')) == (PARENT, 'parent-child'),
            'not the declared nonblocking parent edge')
    require(not value.get('dependents') and value.get('dependency_count') == 1
            and value.get('dependent_count', 0) == 0, 'unexpected dependency counts')
    expected = {} if phase == 'unbound' else {'gc.work_dir': WORK}
    if phase == 'routed':
        expected['gc.routed_to'] = TARGET
    require((value.get('metadata') or {}) == expected, 'task control metadata drift')


def validate_rule_status(raw):
    expected = {b'!! ' + path.encode() for path in RULES}
    entries = raw.split(b'\0')
    require(entries[-1] == b'', 'unterminated Git status')
    require(len(entries[:-1]) == len(expected) and set(entries[:-1]) == expected,
            'candidate contains changes beyond its two pinned ignored policy files')


def running_rows(value, census, action):
    """Admit the real single-worker duplicate display only during suspension.

    Do not change Core's count, erase duplicate rows, or permit a second session.
    The canonical and session rows are two views of one census-bound worker.
    """
    require(action in ('rig-resume', 'city-resume', 'city-suspend', 'rig-suspend'), 'lifecycle action')
    require(isinstance(census, dict) and census.get('ok') is True, 'session census failed')
    sessions = census.get('sessions')
    require(isinstance(sessions, list) and len(sessions) <= 1, 'extra session')
    allowed = {TARGET: ('codex', 'rig')}
    if sessions:
        session = sessions[0]
        require(isinstance(session, dict) and session.get('template') == TARGET
                and not session.get('closed'), 'wrong session template')
        require(session.get('work_dir') == WORK and session.get('rig') == 'gascity'
                and session.get('provider') == 'codex', 'session workspace or provider drift')
        # A fresh live session must carry its native ID and real tmux session name.
        require(isinstance(session.get('id'), str) and bool(session['id'])
                and isinstance(session.get('session_name'), str) and bool(session['session_name']),
                'session identity missing')
        require(session['session_name'] != TARGET, 'ambiguous session identity')
        if action.endswith('-suspend'):
            allowed[session['session_name']] = (session['session_name'], 'city')
    agents = value.get('agents')
    require(isinstance(agents, list), 'agent rows')
    require(all(isinstance(row, dict) and type(row.get('running')) is bool for row in agents), 'agent row shape')
    running = [row for row in agents if row['running']]
    names = [row.get('qualified_name') for row in running]
    require(len(names) == len(set(names)) and set(names) <= set(allowed), 'unexpected running row')
    for row in running:
        require((row.get('name'), row.get('scope')) == allowed[row['qualified_name']], 'running row identity')
    summary = value.get('summary', {})
    require(type(summary.get('running_agents')) is int and summary['running_agents'] == len(running),
            'running count mismatch')
    require(type(summary.get('active_sessions')) is int and 0 <= summary['active_sessions'] <= 1,
            'active session count')
    require(not running or len(sessions) == 1, 'running worker without a session')
    return running


def require_source_scope(paths):
    require(bool(paths) and len(paths) == len(set(paths)), 'empty or duplicate source inventory')
    require(set(paths) <= set(SOURCE_PATHS), 'source change outside the reviewed C1 repair')


def candidate_status(raw):
    """Post-terminal inspection only. Never call Git while a worker is live.

    All staged changes, deletions, renames, policy mutations and extra source
    paths refuse. Evidence is a separate bounded regular-file inventory, not
    a blanket Git-ignore exemption. No claim about its bytes is made here.
    """
    require(raw.endswith(b'\0'), 'unterminated candidate status')
    changes, evidence, rules, seen = [], [], [], set()
    evidence_root = '.gc/worker-evidence/'+TASK+'/'
    for row in raw[:-1].split(b'\0'):
        require(len(row) > 3 and row[2:3] == b' ', 'candidate status record')
        code = row[:2]
        path = row[3:].decode('utf-8', 'strict')
        require(path not in seen and not path.startswith('/')
                and all(part not in ('', '.', '..') for part in path.split('/')), 'candidate path shape')
        seen.add(path)
        if code == b' M' and path in SOURCE_PATHS:
            changes.append(path)
        elif code == b'!!' and path in RULES:
            rules.append(path)
        elif code in (b'??', b'!!') and path.startswith(evidence_root):
            evidence.append(path)
        else:
            raise RuntimeError('unaccepted candidate status or path')
    require_source_scope(changes)
    require(set(rules) == set(RULES), 'candidate policy inventory')
    require(0 < len(evidence) <= 128, 'candidate evidence inventory')
    return dict(source=sorted(changes), evidence=sorted(evidence), rules=sorted(rules))
