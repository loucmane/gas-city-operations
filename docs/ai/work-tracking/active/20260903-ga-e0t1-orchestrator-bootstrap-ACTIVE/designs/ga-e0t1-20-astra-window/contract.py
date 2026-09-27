"""Pure admission rules for the ga-e0t1.20 operational window.

This is not a launch command, provisioning receipt, or worker source repair.
The full raw Bead and runtime observations remain evidence at each caller.
"""
import hashlib
import stat

TASK = 'ga-e0t1.20'
PARENT = 'ga-e0t1'
TARGET = 'gascity/codex'
PROVIDER = 'codex-managed'
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
BOUND_NOTE = 'Operational startup contract for ga-e0t1.20: read /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/WORKER-BRIEF.md sha256 f681228421af8773a5c401e1354b163baef61995ce564427962ccdfb746c5426. Verify and run /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1-20-astra-window/worker-startup.py sha256 7c97d1fcfae3b87ddf76a54a449c34232befb0096b77efde07eb8758b6382de3 inside the actual worker sandbox with its real session ID. No product edit until the coordinator verifies startup and releases that exact session. No staging signing task close restart or delegation. Return an uncommitted candidate only.'

# Core f45a6262 materializes these existing city inputs for an external
# workspace. These are exact possible outputs, not a generic ignored-path
# allowance. The reviewer packet cites the Core producer and prior real output.
RUNTIME_IMAGE = {path:dict(mode=mode,type=stat.S_IFDIR) for path,mode in (
    ('.gc',0o700),('.gc/tmp',0o700),('.gc/scripts',0o755),('.agents/skills',0o755))}
for path,mode,size,digest in (
    ('.gc/settings.json',0o644,5360,'fdd32781975c43c69687c5a9a6ad470f88d2ca54c211a045164a52173d1ef136'),
    ('.gc/scripts/mol-dog-stale-db.sh',0o755,9692,'f201cd2894ad6250d2a5093085b5a136dcc0c4d37299d0af9acc428c4a635522'),
    ('.gc/tmp/skill-catalog-gascity_codex.b64',0o600,3620,'9dd0fb78454c73aeb38c66765506a208600ab77c801d55145e6bbf1a154448d9'),
    ('.agents/skills/.gc-skill-ownership.json',0o644,1348,'f51ef6490bbc3ae9c595b2fe0aaf5a4d825c0db4e5edbc56c59d315e6dc3cf10')):
    RUNTIME_IMAGE[path]=dict(mode=mode,type=stat.S_IFREG,size=size,sha256=digest)
for skill in ('gc-agents','gc-city','gc-dashboard','gc-dispatch','gc-mail','gc-rigs','gc-work'):
    RUNTIME_IMAGE['.agents/skills/core.'+skill]=dict(mode=0o777,type=stat.S_IFLNK,
        target='/home/loucmane/gascity/home/cache/repos/69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f/internal/bootstrap/packs/core/skills/'+skill)
RUNTIME_IMAGE['.agents/skills/gascity.mayor']=dict(mode=0o777,type=stat.S_IFLNK,
    target='/home/loucmane/gascity/home/cache/repos/954ed14987da288bfb98feee4cdab5043a44de1a8a9cf47afaaa0ce6e438fd5f/gascity/skills/mayor')
RUNTIME_FILES={path for path,row in RUNTIME_IMAGE.items() if row['type']!=stat.S_IFDIR}


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
                and session.get('provider') == PROVIDER, 'session workspace or provider drift')
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
    changes, evidence, rules, runtime, seen = [], [], [], [], set()
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
        elif code == b'!!' and path in RUNTIME_FILES:
            runtime.append(path)
        elif code in (b'??', b'!!') and path.startswith(evidence_root):
            evidence.append(path)
        else:
            raise RuntimeError('unaccepted candidate status or path')
    require_source_scope(changes)
    require(set(rules) == set(RULES), 'candidate policy inventory')
    require(0 < len(evidence) <= 128, 'candidate evidence inventory')
    return dict(source=sorted(changes), evidence=sorted(evidence), rules=sorted(rules),runtime=sorted(runtime))
