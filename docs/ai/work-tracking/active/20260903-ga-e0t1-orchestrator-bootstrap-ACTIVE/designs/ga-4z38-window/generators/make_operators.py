"""Generate the round-2b operator wrappers with every digest pinned from the files they run.

Every wrapper follows the reviewed PREP.sh/OBSERVE.sh pattern: umask 0022, the package worktree clean at
the reviewed commit, the fresh-output precondition, each step through the P6 source launcher with its
pinned digest, the first failure stops, the log under the staging directory, and exit with the result.

Usage: python3 -B make_operators.py <package dir>
"""
import hashlib
import os
import sys
from pathlib import Path

HEAD = '''#!/bin/sh
# ga-4z38 window {title}
#
# Runs as a job of the host job runner (designs/gct-jobrunner), a oneshot unit started by the runner.
# Log: ~/.local/share/gas-city-staging/ga-4z38-window/{log}-<timestamp>.txt. Exits with the first failing
# step's result, or 0.
S=/home/loucmane/.local/share/gas-city-staging/ga-4z38-window
W=/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap
D=$W/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs
C=$D/ga-4z38-window
COMMIT=${{1:?usage: {name} <reviewed commit>}}
{pins}
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
mkdir -p "$S" || exit 1
[ ! -L "$S" ] || exit 1
LOG="$S/{log}-$(date -u +%Y%m%dT%H%M%SZ).txt"
exec >"$LOG" 2>&1 </dev/null
echo "== context umask=$(umask) cgroup=$(cat /proc/self/cgroup)"
for ns in ipc mnt net pid time user; do echo "== ns $ns=$(readlink /proc/self/ns/$ns)"; done
[ "$(umask)" = 0022 ] || {{ echo "== STOP: umask is not 0022"; echo "== end"; exit 1; }}
head=$(git -c core.fsmonitor=false -C "$W" rev-parse HEAD) || head=unreadable
status=$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$W" --no-optional-locks status --porcelain --untracked-files=all) || status=unreadable
if [ "$head" != "$COMMIT" ] || [ -n "$status" ]; then
  echo "== STOP: package worktree head=$head not clean or not the reviewed commit"; echo "== end"; exit 1
fi
{pre}step() {{
  label=$1; shift
  echo "== $label $(date -u +%H:%M:%SZ)"
  /usr/bin/python3 -I -S -B "$D/gct-m1wh-p6/source-launch.py" "$@"
  rc=$?
  if [ "$rc" != 0 ]; then
    echo "== {upper} REFUSED at $label rc=$rc: read this log and the named roots before any further step"
    echo "== end $(date -u +%H:%M:%SZ)"; exit "$rc"
  fi
}}
'''

TAIL = '''echo "== {upper} PASS"
echo "== end $(date -u +%H:%M:%SZ)"
exit 0
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def absent(*paths):
    lines = ''.join('{ [ ! -e %s ] && [ ! -L %s ]; } || { echo "== STOP: output root already used: %s"; '
                    'echo "== end"; exit 1; }\n' % (p, p, p) for p in paths)
    return lines


def main(package):
    package = Path(package)
    out = Path(os.environ.get('GA4Z38_OUT', package))
    d = {name: sha(out/name) for name in ('reconcile-predecessor-r3.py', 'observe-integrity-r11.py', 'window-r11.py',
                                          'freshen-r11.py', 'hold-r11.py', 'restore-admission-r3.py',
                                          'release-r11.py', 'close-r11.py', 'budget-r11.py',
                                          'bind-task-r3.py', 'route-task-r5.py',
                                          'audit-queue-r3.py', 'observe-terminal-r11.py', 'watch-r11.py')}
    window = '/var/tmp/ga-4z38-window-20260923-r1'
    wrappers = {
        'RECONCILE.sh': dict(title='reconcile: the reviewed status-only hold of the consumed predecessor ga-y49e\n'
                                   '# (blocked, route and evidence preserved), before BIND.',
                             pins='RECONCILE_SHA=%s' % d['reconcile-predecessor-r3.py'],
                             pre=absent('/var/tmp/ga-4z38-reconcile-20260923-r1'),
                             steps=['step reconcile "$C/reconcile-predecessor-r3.py" "$RECONCILE_SHA"']),
        'FRESHEN.sh': dict(title='freshen: refresh relatime access times of every exact-compared object, before\n'
                                 '# OBSERVE. Reads only; repeatable, one fresh root per run; refuses while any object is\n'
                                 '# still too old to refresh (see its old.json).',
                           pins='FRESHEN_SHA=%s' % d['freshen-r11.py'],
                           pre=absent('/var/tmp/ga-4z38-integrity-20260923-r1', window),
                           steps=['step freshen "$C/freshen-r11.py" "$FRESHEN_SHA"']),
        'OBSERVE.sh': dict(title='observe: the fresh accepted-state admission plus a full native integrity read,\n'
                                 '# immediately before PREFLIGHT.sh. It writes only its root and the log, installs nothing\n'
                                 '# and launches no worker. Outside the read-only sandbox it runs gc status, gc session\n'
                                 '# list and the provisioner go-version probe; the pinned inspector runs in read-only bwrap.',
                           pins='OBSERVE_SHA=%s' % d['observe-integrity-r11.py'],
                           pre=absent('/var/tmp/ga-4z38-integrity-20260923-r1'),
                           steps=['step observe "$C/observe-integrity-r11.py" "$OBSERVE_SHA"']),
        'BIND.sh': dict(title='bind: the one supported ga-4z38 contract/enrollment patch, before the window.\n'
                              '# It appends the reviewed worker brief and the requested native attempt metadata to\n'
                              '# ga-4z38. It never routes, resumes or launches a worker.',
                        pins='BIND_SHA=%s' % d['bind-task-r3.py'],
                        pre=absent('/var/tmp/ga-4z38-bind-20260923-r1', window),
                        steps=['step bind "$C/bind-task-r3.py" "$BIND_SHA"']),
        'PREFLIGHT.sh': dict(title='preflight: read-only admission of the window against the fresh integrity\n'
                                   '# observation (OBSERVE.sh). It creates the window root and stages nothing.',
                             pins='WINDOW_SHA=%s\nFRESHEN_SHA=%s' % (d['window-r11.py'], d['freshen-r11.py']),
                             pre=absent(window)
                                 + '# An object already fresh at FRESHEN may be up to 19 hours old; it must stay under 24\n'
                                   '# hours until T0 plus four hours, so PREFLIGHT must follow a FRESHEN pass within 45 min.\n'
                                   'find /var/tmp -maxdepth 2 -path "/var/tmp/ga-4z38-freshen-*/result.json" -mmin -45 '
                                   '-exec grep -l \'"ok": true\' {} + | xargs -r grep -l "$FRESHEN_SHA" | grep -q . || '
                                   '{ echo "== STOP: no FRESHEN pass in the last 45 minutes"; '
                                   'echo "== end"; exit 1; }\n',
                             steps=['step preflight "$C/window-r11.py" "$WINDOW_SHA" preflight']),
        'STAGE.sh': dict(title='stage: the single-worker overlay city and its native-finalized receipt, through\n'
                               '# the confined writers and one observed reload. Every rig stays suspended.',
                         pins='WINDOW_SHA=%s' % d['window-r11.py'],
                         pre='[ -e %s/preflight-pass.json ] && [ ! -e %s/stage-consumed.json ] || '
                             '{ echo "== STOP: window not preflighted or stage already consumed"; echo "== end"; exit 1; }\n'
                             % (window, window),
                         steps=['step stage "$C/window-r11.py" "$WINDOW_SHA" stage']),
        'ROUTE.sh': dict(title='route: one raw route of the bound task while every rig is suspended, then the\n'
                               '# read-only sole-task queue audit.',
                         pins='ROUTE_SHA=%s\nAUDIT_SHA=%s' % (d['route-task-r5.py'], d['audit-queue-r3.py']),
                         pre=absent('/var/tmp/ga-4z38-route-20260923-r1', '/var/tmp/ga-4z38-audit-route-20260923-r1'),
                         steps=['step route "$C/route-task-r5.py" "$ROUTE_SHA"',
                                'step audit-route "$C/audit-queue-r3.py" "$AUDIT_SHA" route']),
        'RESUME.sh': dict(title='resume: rig-resume, the read-only queue audit, then city-resume, once each.',
                          pins='WINDOW_SHA=%s\nAUDIT_SHA=%s' % (d['window-r11.py'], d['audit-queue-r3.py']),
                          pre='[ -e /var/tmp/ga-4z38-route-20260923-r1/result.json ] && '
                              '[ -e /var/tmp/ga-4z38-audit-route-20260923-r1/result.json ] || '
                              '{ echo "== STOP: ROUTE has not passed"; echo "== end"; exit 1; }\n'
                              + absent('/var/tmp/ga-4z38-audit-resume-20260923-r1', window + '/rig-resume-started.json'),
                          steps=['step rig-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle rig-resume',
                                 'step audit-resume "$C/audit-queue-r3.py" "$AUDIT_SHA" resume',
                                 'step city-resume "$C/window-r11.py" "$WINDOW_SHA" lifecycle city-resume']),
        'WATCH.sh': dict(title='watch: read-only in-window observation; repeatable, one fresh root per run.',
                         pins='WATCH_SHA=%s' % d['watch-r11.py'],
                         pre='',
                         steps=['step watch "$C/watch-r11.py" "$WATCH_SHA"']),
        'CONTAIN.sh': dict(title='contain: hold scheduling. city-suspend (only if the city was resumed), then\n'
                                 '# rig-suspend, once each, through the reviewed lifecycle.',
                           pins='WINDOW_SHA=%s' % d['window-r11.py'],
                           pre='[ -e %s/stage-pass.json ] || { echo "== STOP: no staged window"; echo "== end"; exit 1; }\n'
                               % window,
                           steps=['if [ -e %s/suspension-city-resume-event.json ] && '
                                  '[ ! -e %s/suspension-city-suspend-event.json ]; then\n'
                                  '  step city-suspend "$C/window-r11.py" "$WINDOW_SHA" lifecycle city-suspend\n'
                                  'fi' % (window, window),
                                  'if [ -e %s/suspension-rig-resume-event.json ] && '
                                  '[ ! -e %s/suspension-rig-suspend-event.json ]; then\n'
                                  '  step rig-suspend "$C/window-r11.py" "$WINDOW_SHA" lifecycle rig-suspend\n'
                                  'fi' % (window, window)]),
        'SOURCE-RELEASE.sh': dict(title='source release: validate the coordinator source release against the live\n'
                                        '# worker session, post it once to the ga-4z38 notes, read it back and nudge.\n'
                                        '# Repeatable: a run after the post only verifies and nudges again.',
                                  pins='RELEASE_SHA=%s\nBUDGET_SHA=%s' % (d['release-r11.py'], d['budget-r11.py']),
                                  pre='',
                                  steps=['step budget "$C/budget-r11.py" "$BUDGET_SHA" 100',
                                         'step source-release "$C/release-r11.py" "$RELEASE_SHA" source']),
        'SIGNING-RELEASE.sh': dict(title='signing release: validate the coordinator signing release against the live\n'
                                         '# worker session and the staged index, post it once, read it back and nudge.\n'
                                         '# Repeatable: a run after the post only verifies and nudges again.',
                                   pins='RELEASE_SHA=%s\nBUDGET_SHA=%s' % (d['release-r11.py'], d['budget-r11.py']),
                                   pre='[ -e /var/tmp/ga-4z38-source-release.posted ] || '
                                       '{ echo "== STOP: no source release posted"; echo "== end"; exit 1; }\n',
                                   steps=['step budget "$C/budget-r11.py" "$BUDGET_SHA" 85',
                                          'step signing-release "$C/release-r11.py" "$RELEASE_SHA" signing']),
        'CLOSE.sh': dict(title='close: after CONTAIN (or a passing HOLD), drain once (best-effort) and close the one\n'
                               '# worker session, then prove zero session, pane and worktree-process residue.\n'
                               '# Repeatable: a rerun never repeats the drain and closes only a still-open session.',
                         pins='CLOSE_SHA=%s' % d['close-r11.py'],
                         pre='',
                         steps=['step close "$C/close-r11.py" "$CLOSE_SHA"']),
        'HOLD.sh': dict(title='hold: emergency scheduling hold for a STRANDED window only (a lifecycle failure record\n'
                              '# exists, so CONTAIN.sh cannot act). Suspends the city and the gascity rig; never\n'
                              '# replays lifecycle, never restores, writes nothing in the window root.',
                        pins='HOLD_SHA=%s' % d['hold-r11.py'],
                        pre='[ -e %s/stage-consumed.json ] || { echo "== STOP: no staged window"; echo "== end"; exit 1; }\n'
                            % window,
                        steps=['step hold "$C/hold-r11.py" "$HOLD_SHA"']),
        'ADMIT.sh': dict(title='admit: the read-only restore admission (full preservation check, terminal lifecycle,\n'
                               '# quiescent host) after CONTAIN and the session close. RESTORE.sh requires its pass.',
                         pre='[ -e %s/stage-consumed.json ] && [ ! -e %s/restore-consumed.json ] || '
                             '{ echo "== STOP: no owned window or restore already consumed"; echo "== end"; exit 1; }\n'
                             % (window, window) + absent(window + '/restore-admission.json')
                             + 'find /var/tmp -maxdepth 2 -path "/var/tmp/ga-4z38-close-*/result.json" '
                               '-exec grep -l \'"ok": true\' {} + | xargs -r grep -l "$CLOSE_SHA" | grep -q . || '
                               '{ echo "== STOP: CLOSE has not passed"; echo "== end"; exit 1; }\n',
                         pins='ADMIT_SHA=%s\nBUDGET_SHA=%s\nCLOSE_SHA=%s' % (d['restore-admission-r3.py'], d['budget-r11.py'],
                                                                         d['close-r11.py']),
                         steps=['step budget "$C/budget-r11.py" "$BUDGET_SHA" 40',
                                'step admit "$C/restore-admission-r3.py" "$ADMIT_SHA"']),
        'RESTORE.sh': dict(title='restore: the exact baseline city and receipt, once, after terminal suspension\n'
                                 '# and containment.',
                           pins='WINDOW_SHA=%s\nBUDGET_SHA=%s' % (d['window-r11.py'], d['budget-r11.py']),
                           pre='[ -e %s/restore-admission-pass.json ] && [ ! -e %s/restore-consumed.json ] || '
                               '{ echo "== STOP: restore admission has not passed or restore already consumed"; '
                               'echo "== end"; exit 1; }\n'
                               % (window, window),
                           steps=['step budget "$C/budget-r11.py" "$BUDGET_SHA" 25',
                                  'step restore "$C/window-r11.py" "$WINDOW_SHA" restore']),
        'TERMINAL.sh': dict(title='terminal: the full native integrity observation of the restored baseline,\n'
                                  '# bound to the terminal suspension endpoint and the accepted restoration.',
                            pre=absent('/var/tmp/ga-4z38-terminal-20260923-r1'),
                            pins='TERMINAL_SHA=%s\nBUDGET_SHA=%s' % (d['observe-terminal-r11.py'], d['budget-r11.py']),
                            steps=['step budget "$C/budget-r11.py" "$BUDGET_SHA" 8',
                                   'step terminal "$C/observe-terminal-r11.py" "$TERMINAL_SHA"']),
    }
    # The job runner starts a wrapper path at most once per commit (gct-jobrunner A4). Steps that must be
    # able to run more than once get numbered slots: identical steps, distinct reviewed wrapper paths.
    for base, count in (('FRESHEN', 3), ('WATCH', 8), ('SOURCE-RELEASE', 3), ('SIGNING-RELEASE', 3), ('CLOSE', 2),
                        ('HOLD', 2)):
        spec = wrappers.pop(base + '.sh')
        for slot in range(1, count + 1):
            wrappers['%s-%d.sh' % (base, slot)] = dict(
                spec, title=spec['title'] + '\n# Slot %d of %d: the job runner starts each wrapper path once per commit.'
                % (slot, count))
    (out/'operator').mkdir(exist_ok=True)
    for name, spec in wrappers.items():
        log = name[:-3].lower()
        text = HEAD.format(title=spec['title'], log=log, name=name, pins=spec['pins'], pre=spec['pre'],
                           upper=name[:-3]) + '\n'.join(spec['steps']) + '\n' + TAIL.format(upper=name[:-3])
        (out/'operator'/name).write_text(text)
        print(name, sha(out/'operator'/name))


if __name__ == '__main__':
    main(sys.argv[1])
