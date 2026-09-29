"""Pure admission rules for the fresh ga-x2wz operational window.

Preparation component only: no executor, launch, route or permission grant.
The successful R11 runtime-image and single-session rules are preserved. Its
consumed claims, retry notes and startup-file exceptions are NOT inherited.
"""
import hashlib
import json
import re
import stat

TASK = 'ga-x2wz'
PARENT = 'ga-e0t1'
TARGET = 'gascity/codex'
PROVIDER = 'codex-managed'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-x2wz'
BASE = 'bf369ae41cf512f5f5563f842cadff394457da4c'
BRANCH = 'codex/ga-x2wz-c1-package'
# Fresh same-store readback; parent audit history is not worker input.
BASELINE = json.loads("{\"id\":\"ga-x2wz\",\"title\":\"Build executable C1 handover window package\",\"description\":\"Candidate only implementation of the accepted C1 d11 window contract in Operations. Reuse exact gct-e8ex s5 predecessor and accepted image r3 and slots without another design cycle. Produce deterministic package assembly, generated bounded executors and isolated regression fixtures. Use one fresh Gas City Astra high worker with reviewed startup probes and acknowledged release. No C1 launch or changes to Template tasks, live settings, rigs or protected projects by the worker. No signing, push, delegation or activation by the worker. Preserve all historical packages and evidence.\",\"acceptance_criteria\":\"Exact signed Operations base and scope bound before dispatch. Proven startup capability and single claim before any edit. Deterministic generation with asserted predecessor digests and replacement counts. Positive and negative offline tests cover every accepted C1 safety invariant including controller cgroup quiet points, bounded live census, tmux jobs, slot arbitration, close self admission, restore deadlines and create only evidence. Two independent read only reviews pass on the exact candidate. All worker files inventoried, unrelated inputs unchanged, supported drain and suspension with zero residue. Candidate only closure does not prove C1 execution or provider parity.\",\"notes\":\"Preparation checkpoint only Exact intended signed base bf369ae41cf512f5f5563f842cadff394457da4c with candidate workspace ga-x2wz and branch codex/ga-x2wz-c1-package No worker workspace or branch created Automatic review twice refused coordinator materialization of mechanically rebound workspace controls before any write The second decision followed exact unchanged function proof and reread of standing authority No bypass or runtime mutation The only saved files are preparation evidence and ledger readback Await specific coordinator preparation exception with independent review before execution All C1 implementation remains Gas City worker only The task stays open unassigned and unrouted\\nOperator approved the explicit bounded coordinator preparation exception on 20260929 It covers this tasks workspace and launch controls including exact task base file scope bindings and tests with independent review before execution Actual C1 implementation remains Gas City worker only Previous refusals remain preserved No worker launched No workspace created Task remains open unassigned and unrouted\\nWORKTREE PASS at signed 1e4ac7ac after two independent Astra passes Result a538ebb3 binds exact clean workspace and frozen signed base bf369ae4 Both local rule files installed with global default unchanged Job ended inactive and exit zero No worker route claim receipt install or rig transition Task remains open unassigned and unrouted Next is uninstalled PREP and reviewed worker window Never replay completed WORKTREE All evidence preserved\\nPREP PASS at exact signed 60320d683017e7a4a6fda617e268a2ae73ac10df after two independent Astra passes Result 21ad0d154fcb3d0ddf03b7ce2d708d41669495e12115316741441c741d6d86bd binds uninstalled one worker configuration and unchanged typed profiles Only two receipt fields changed in the uninstalled output Job ended inactive exit zero No worker launch claim route or rig transition occurred Completed WORKTREE and PREP are not repeatable Next is complete independently reviewed worker window Task remains open unassigned and unrouted\",\"status\":\"open\",\"priority\":2,\"issue_type\":\"task\",\"owner\":\"lookmanbenali@gmail.com\",\"created_at\":\"2026-09-29T10:24:47Z\",\"created_by\":\"loucmane\",\"updated_at\":\"2026-09-29T11:21:34Z\",\"labels\":[\"candidate\",\"handover\",\"workflow\"],\"dependencies\":[{\"id\":\"ga-e0t1\",\"dependency_type\":\"relates-to\"}],\"dependent_count\":0,\"dependency_count\":1,\"comment_count\":0}")
DESCRIPTION = hashlib.sha256(BASELINE['description'].encode()).hexdigest()
ACCEPTANCE = hashlib.sha256(BASELINE['acceptance_criteria'].encode()).hexdigest()
UNBOUND_NOTE = BASELINE['notes']
BIND_NOTE = "Operational startup contract for ga-x2wz. Completed WORKTREE and PREP bind the exact clean workspace and signed base. Scope is create only and finite at /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-x2wz-c1-package/FILE-SCOPE.json sha256 3ffdeb52a9d527d3a598cde728ecea590baca02ef10b4c61bd5a952de697f31e. New product parent directories use mode 0755. Read /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-x2wz-c1-package/WORKER-BRIEF.md sha256 c389dc4a1a624c8cf0193e346fc1b8fb230a08dfee47d512915c717ff9c1b6b8 and /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-x2wz-c1-package/PRECLAIM.md sha256 2b0bf9bae1983e7efd8015233d45c9e26db9cc1d360b7c271b97e498ec8f1d58. Verify and run /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-x2wz-c1-package/worker-startup.py sha256 b7c33d703ebc2ba30df2074ea392abcdb94b7c596cc4b27d3ab42d2bf8e80c3c only in the actual worker sandbox with its real session ID. Fresh startup proof including two immutable predecessor reads and one acknowledged same session release are mandatory before editing. Preserve subscription only authentication sandbox and native denials candidate only scope and all historical evidence. No staging signing commits pushes task close native delegation installs or live product execution. New evidence belongs only in .gc/worker-evidence/ga-x2wz/r1. Return an uncommitted candidate only."
BOUND_NOTE = UNBOUND_NOTE + '\n' + BIND_NOTE
RULES = {
    '.codex/rules/gas-city-native-control.rules': '0a2c32485d71ef31875010ea810deffb0f2936e8c89bb5da2f7f2aeed5044123',
    '.codex/rules/window-restrictions.rules': 'ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773',
}
DEFAULT_RULES = '3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516'
SCOPE_ROOT = "docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/"
SOURCE_MODES = json.loads("{\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/README.md\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/audit-queue-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/bind-task-r5.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/budget-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-census.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-contract.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-probe.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/c1-store.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/cache-atime-policy-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/close-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/common-snapshot-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/generators/make_successor.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/h1-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/hold-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/image1-record-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/observe-integrity-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/observe-terminal-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/ADMIT.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/BIND.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/CLOSE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/CONTAIN-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/H1.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/HOLD-1.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/HOLD-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/OBSERVE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/PREFLIGHT.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/PREP.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/RESTORE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/RESUME.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/ROUTE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/STAGE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/TERMINAL.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WATCH-LOOP-2.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WATCH-LOOP.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/operator/WORKTREE.sh\":493,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/pin-s1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/prep-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/restore-admission-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/restore-r9-routes-r3.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/route-chain-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/route-task-r5.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/s1-pins.json\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/suspension-lineage.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_c1_contract.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_successor.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/test_watch_loop.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/watch-loop-r1.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/watch-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-base-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-obs-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/window-r11.py\":420,\"docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/worktree-task-r1.py\":420}")
SOURCE_PATHS = tuple(SOURCE_MODES)
MAX_PRODUCT_BYTES = 2 << 20
EVIDENCE_ROOT = '.gc/worker-evidence/ga-x2wz/r1/'

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
RUNTIME_IMAGE['.codex/hooks.json']={'mode': 420, 'type': 32768, 'size': 1238, 'sha256': '55e21a9d981805afb62da110b022bc847f7ad2b9a62bada45de95dbdfa472410'}
RUNTIME_FILES={path for path,row in RUNTIME_IMAGE.items() if row['type']!=stat.S_IFDIR}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def own_fields(value):
    require(isinstance(value, dict), 'task shape')
    return {key: val for key, val in value.items()
            if key not in ('dependencies', 'dependents', 'metadata', 'notes', 'updated_at')}


def validate_task(value, phase):
    """Fresh task only: the informational edge and pre-existing notes persist."""
    require(phase in ('unbound', 'bound', 'routed'), 'task phase')
    require(own_fields(value) == own_fields(BASELINE), 'task own fields differ')
    require(value.get('status') == 'open' and not value.get('assignee')
            and 'parent' not in value, 'task is owned or has a parent')
    require(value.get('notes') == (UNBOUND_NOTE if phase == 'unbound' else BOUND_NOTE),
            'task evidence or startup contract differs')
    deps = value.get('dependencies')
    require(isinstance(deps, list) and len(deps) == 1 and isinstance(deps[0], dict),
            'dependency cardinality')
    require((deps[0].get('id'), deps[0].get('dependency_type')) == (PARENT, 'relates-to'),
            'informational relationship differs')
    require(not value.get('dependents') and value.get('dependency_count') == 1
            and value.get('dependent_count') == 0, 'unexpected dependency counts')
    expected = {} if phase == 'unbound' else {'gc.work_dir': WORK}
    if phase == 'routed':
        expected['gc.routed_to'] = TARGET
    actual = value.get('metadata', {})
    require(isinstance(actual, dict) and actual == expected, 'task control metadata drift')


def validate_binding_delta(before, after):
    validate_task(before, 'unbound')
    validate_task(after, 'bound')
    require(after['notes'] == before['notes'] + '\n' + BIND_NOTE, 'notes not append-forward')
    for key in set(before) | set(after):
        if key not in ('metadata', 'notes', 'updated_at'):
            require(before.get(key) == after.get(key), 'unexpected binding delta: ' + key)


def validate_route_delta(before, after):
    validate_task(before, 'bound')
    validate_task(after, 'routed')
    for key in set(before) | set(after):
        if key not in ('metadata', 'updated_at'):
            require(before.get(key) == after.get(key), 'unexpected route delta: ' + key)


def validate_rule_status(raw):
    # Fresh prelaunch workspace: Core has not materialized runtime files yet.
    expected = {b'!! ' + path.encode() for path in RULES}
    require(isinstance(raw, bytes) and raw.endswith(b'\0'), 'unterminated Git status')
    entries = raw[:-1].split(b'\0')
    require(len(entries) == len(expected) and set(entries) == expected,
            'fresh workspace contains more than its exact two policy files')


def close_identity(session):
    require(isinstance(session,dict) and session.get('template')==TARGET
            and session.get('rig')=='gascity' and session.get('provider')==PROVIDER
            and session.get('work_dir')==WORK and not session.get('closed'), 'close worker capability differs')
    for key in ('id','session_name'):
        require(isinstance(session.get(key),str)
                and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{1,127}',session[key]), 'close identity missing')
    require(isinstance(session.get('created_at'),str) and session['created_at'], 'close creation identity missing')
    return {key:session.get(key) for key in ('id','session_name','template','rig','provider','work_dir','worker_dir','created_at')}


def close_census(value, expected):
    require(isinstance(value,dict) and value.get('ok') is True
            and isinstance(value.get('sessions'),list) and len(value['sessions'])<=1, 'close census not singleton')
    rows=value['sessions']
    if rows:require(close_identity(rows[0])==expected, 'close session substituted or not bound')
    return rows


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
    active_sessions = summary.get('active_sessions')
    if 'active_sessions' not in summary:
        # The Core integer field is omitempty. Accept only its absent-zero form,
        # corroborated by a complete independent census and no running rows.
        # A suspended record is not an active session; still bind its identity
        # above and require its explicit state rather than guessing from count.
        counts = census.get('summary')
        expected = dict(total=len(sessions), active=0, suspended=len(sessions), closed=0)
        require(isinstance(counts, dict) and not running
                and all(type(counts.get(key)) is int and counts[key] == count
                        for key, count in expected.items())
                and all(session.get('state') == 'suspended' for session in sessions),
                'omitted active session count lacks independent zero proof')
        active_sessions = 0
    require(type(active_sessions) is int and 0 <= active_sessions <= len(sessions),
            'active session count')
    require(not running or len(sessions) == 1, 'running worker without a session')
    return running


def close_claim(task, session, admitted=None):
    # No historical failed-claim allowance from R11. An unclaimed new session
    # may close only against the exact admitted, fresh routed task.
    close_identity(session)
    require(task.get('id') == TASK and task.get('status') in ('open', 'in_progress'),
            'close task identity or state')
    for key, digest in (('description', DESCRIPTION), ('acceptance_criteria', ACCEPTANCE)):
        require(isinstance(task.get(key), str)
                and hashlib.sha256(task[key].encode()).hexdigest() == digest,
                'close task contract differs')
    metadata = task.get('metadata')
    require(isinstance(metadata, dict) and metadata.get('gc.work_dir') == WORK
            and metadata.get('gc.routed_to') == TARGET, 'close route or workspace differs')
    owner = {'gc.session_id': session['id'], 'gc.session_name': session['session_name']}
    if task['status'] == 'open':
        require(isinstance(admitted, dict) and task == admitted, 'unclaimed task differs from admission')
        validate_task(admitted, 'routed')
    else:
        require(task.get('assignee') == session['session_name']
                and all(metadata.get(key) == val for key, val in owner.items()),
                'close claim owner differs')


def require_source_scope(paths):
    require(bool(paths) and len(paths) == len(set(paths)), 'empty or duplicate source inventory')
    require(set(paths) == set(SOURCE_PATHS), 'candidate must contain the exact create-only C1 file scope')


def candidate_status(raw):
    """Post-terminal only; byte/mode/evidence bounds are checked by the inspector."""
    require(isinstance(raw, bytes) and raw.endswith(b'\0'), 'unterminated candidate status')
    changes, evidence, rules, runtime, seen = [], [], [], [], set()
    for row in raw[:-1].split(b'\0'):
        require(len(row) > 3 and row[2:3] == b' ', 'candidate status record')
        code, path = row[:2], row[3:].decode('utf-8', 'strict')
        require(path not in seen and not path.startswith('/')
                and all(part not in ('', '.', '..') for part in path.split('/')),
                'candidate path shape')
        seen.add(path)
        if code == b'??' and path in SOURCE_PATHS:
            changes.append(path)
        elif code == b'!!' and path in RULES:
            rules.append(path)
        elif (code == b'!!' and path in RUNTIME_FILES) or (code == b'??' and path == '.codex/hooks.json'):
            runtime.append(path)
        elif code in (b'??', b'!!') and path.startswith(EVIDENCE_ROOT):
            evidence.append(path)
        else:
            raise RuntimeError('unaccepted candidate status or path')
    require_source_scope(changes)
    require(set(rules) == set(RULES), 'candidate policy inventory')
    require(0 < len(evidence) <= 128, 'candidate evidence inventory')
    return dict(source=sorted(changes), evidence=sorted(evidence), rules=sorted(rules), runtime=sorted(runtime))
