"""Pure r5 launch contract: no execution, grants, trust writes or lifecycle.

The installed Core produces this one hooks image. It was preserved after r4;
accepting its exact bytes is not a hooks-trust assertion. The actual client
must still prove native policy and sandbox behavior before source release.
"""
import copy
import hashlib
import re
import stat

GC = '/home/loucmane/gascity/bin/gc'
CITY = '/home/loucmane/gascity/city'
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-x2wz'
TASK = 'ga-x2wz'
HOOK = '.codex/hooks.json'
HOOK_IMAGE = dict(mode=0o644, type=stat.S_IFREG, size=1238,
    sha256='55e21a9d981805afb62da110b022bc847f7ad2b9a62bada45de95dbdfa472410')
CLAIM = (GC, 'hook', '--claim', '--drain-ack', '--json', '--city', CITY, '--rig', 'gascity')
SHOW = (GC, 'bd', 'show', TASK, '--city', CITY, '--rig', 'gascity')
UPDATE = (GC, 'bd', 'update', TASK, '--city', CITY, '--rig', 'gascity', '--append-notes')
DRAIN = (GC, 'runtime', 'drain-ack', '--city', CITY, '--rig', 'gascity')


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def startup_status(raw):
    # The Core-generated, nonignored hook is the ONLY nontracked input.
    # Its content/authority is checked separately, not inferred from Git text.
    require(raw == b'?? .codex/hooks.json\0', 'unexpected pre-edit Git status')


def hook_image(raw, metadata):
    require(metadata == dict(HOOK_IMAGE, uid=1000, gid=1000, nlink=1),
            'generated hook authority differs')
    require(len(raw) == HOOK_IMAGE['size'] and hashlib.sha256(raw).hexdigest() == HOOK_IMAGE['sha256'],
            'generated hook bytes differ')


def initial_runtime_image(before, after, runtime):
    """The restored r4 output is now required, never silently regenerated."""
    expected = dict(before)
    for path, row in dict(runtime, **{HOOK: HOOK_IMAGE}).items():
        require(path not in before, 'runtime path was already in original baseline')
        expected[path] = row
    require(after == expected, 'restored workspace differs from exact r4 output')


def config_delta(before, after, prompt_path):
    """Only one existing agent's prompt changes, no provider/options grant."""
    expected = copy.deepcopy(before)
    rows = expected['config']['Agents']
    chosen = [row for row in rows if (row.get('Dir'), row.get('Name')) == ('gascity', 'codex')]
    require(len(chosen) == 1 and chosen[0].get('Provider') == 'codex-managed', 'launch agent identity')
    chosen[0]['PromptTemplate'] = prompt_path
    require(after == expected, 'unexpected prompt configuration delta')


def prompt_body(actual, body):
    # Core prepends its time-varying beacon and appends an assigned-skills
    # catalog. The middle body must be exact and occur once, before any claim.
    require(isinstance(actual, str) and isinstance(body, str) and body, 'prompt type')
    require(actual.count(body) == 1, 'startup prompt missing duplicated or changed')
    prefix, suffix = actual.split(body)
    require(re.fullmatch(r'\[city\] gascity/codex \u2022 \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        r'\n\nRun `gc prime` to initialize your context\.\n\n', prefix),
            'unexpected startup beacon')
    # Bind the exact known catalog in the package assembler, not here. Returning
    # it never accepts it; callers must compare its hash with their frozen pin.
    return hashlib.sha256(suffix.encode()).hexdigest()


def retry_status(status, census, action):
    """The one observed torn read is retryable, never accepted as success.

    A following independently valid status+census must pass the existing full
    validator within the unchanged deadline. No lifecycle command is repeated.
    """
    if action not in ('city-suspend', 'rig-suspend'):
        return False
    summary = status.get('summary', {})
    rows = status.get('agents')
    return (type(summary.get('active_sessions')) is int and summary['active_sessions'] == 1
        and type(summary.get('running_agents')) is int and summary['running_agents'] == 0
        and isinstance(rows, list) and all(isinstance(r, dict) and r.get('running') is False for r in rows)
        and census.get('ok') is True and census.get('sessions') == []
        and census.get('summary') == dict(total=0, active=0, suspended=0, closed=0))
