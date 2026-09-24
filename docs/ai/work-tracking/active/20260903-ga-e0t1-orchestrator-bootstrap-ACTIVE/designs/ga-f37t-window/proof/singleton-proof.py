"""Read-only proof, before ROUTE, that the capped worker is not drained while it owns ga-f37t.

gc warns for this overlay that "max_active_sessions=1 creates a canonical singleton that drains when
scale_check returns 0" (prep-r11.py SINGLETON_WARNING). After the claim, ga-f37t is in_progress and
assigned, so the default scale_check (ready, unassigned, routed demand) returns 0 while the worker
waits for a release. This proof checks that the session is still preserved:
1. The overlay's effective config (prep config.isolated.json) gives the worker no custom ScaleCheck or
   WorkQuery, so the default demand probe applies.
2. Core at the worker base e6366b9e (the PR 45 merge the installed gc was built from):
   - internal/config/workquery.go: the default count form "counts ready, unassigned, routed demand";
   - cmd/gc/pool_desired_state.go: new-session demand comes from scale_check, while the desired-state
     computation "only preserves sessions that already own actionable work", and its resume tier keeps
     a session whose assigned work bead is in_progress or open.
3. The session survives its idle waits (a restart would be refused: BIND stamps the task attempt, and
   Core taskattempt.Start never starts an attempt twice). In the pinned overlay config
   (config.isolated.json 6c4b44c4) the worker has no idle_timeout, no max_session_age and no
   sleep_after_idle; the gascity rig's and the workspace's session_sleep defaults are empty, so Core
   ResolveSessionSleepPolicy returns off (legacy_off); claim_holder_stall_timeout is unset. The city's
   progress_stall_timeout (5m) restarts only a claim-less session (session_progress.go
   sessionProgressStalled returns false for a claim holder); for a claim holder Core only marks the
   claimed work with the needs/operator label and progress-stall metadata, never its status or assignee
   (session_reconciler.go markProgressStalledClaimedWorkNeedsOperator). AssignedWorkDeferLimit bounds
   only the idle-timeout ladder, which is off. [chat_sessions] idle_timeout is unset too. The managed
   signer (managed-git-commit, managed-git-signerd) treats the Bead only as an identity string checked
   against its policy prefix: both files import only the standard library, name no bd or gc executable,
   and contain no assignee, label, needs/operator, progress_stall, controller_error or failure_ reference.
   So the mark cannot refuse the signature. The mark does not end the session either: the resume tier
   that keeps a claim holder's session (pool_desired_state.go) filters its work only by status, assignee
   and route, never by label or metadata, and no non-test Core code reads needs/operator except the
   provider-failure writer's own de-duplication. Nor does any cmd/gc code read the mark's metadata keys
   except the stall-signature de-duplication (the internal/api run view and internal/dispatch workflow
   rows read failure_reason and controller_error for display and workflow roots, not sessions). The
   actionable-work collector that feeds the resume tier lists in_progress work by status and keeps it
   by assignee only (build_desired_state.go appendInProgressWorkUnique).
All reads are git object reads (GIT_OPTIONAL_LOCKS=0), an O_NOATIME read of the prep evidence file, and
plain reads of the two root-owned signer sources (O_NOATIME needs ownership). The proof runs before
PREFLIGHT, never in the window. Nothing is written.

Usage: python3 -B singleton-proof.py   (prints one JSON object; exit 0 only if every check holds)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG = Path('/var/tmp/ga-f37t-prep-20260923-r2/config.isolated.json')
CONFIG_SHA = '6c4b44c48c189171eb6ed0870e587c915f8af9e3053392cc877974024f2ab412'
SIGNER = ('/usr/local/libexec/gas-city/managed-git-commit', '/usr/local/libexec/gas-city/managed-git-signerd')
CORE = '/home/loucmane/gascity-core-worktrees/ga-f37t-typed-route-cycles'
BASE = 'e6366b9ececd3a4ceab2bcaa264a5e317e6eab88'
ENV = dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME='/home/loucmane', GIT_OPTIONAL_LOCKS='0', LC_ALL='C.UTF-8')


def show(path):
    p = subprocess.run(['/usr/bin/git', '-C', CORE, 'show', BASE + ':' + path], env=ENV, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-300:]
    return p.stdout


def noatime(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    except PermissionError:  # O_NOATIME needs file ownership; the signer sources are root-owned
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        raw = b''
        while chunk := os.read(fd, 1 << 20):
            raw += chunk
    finally:
        os.close(fd)
    return raw


def imports_are_stdlib(text):
    names = re.findall(rb'^\s*(?:from|import) ([A-Za-z_][A-Za-z0-9_]*)', text, re.M)
    return bool(names) and all(name.decode() in sys.stdlib_module_names or name == b'__future__' for name in names)


def main():
    raw = noatime(CONFIG)
    city = json.loads(raw)['config']
    agents = city['Agents']
    [worker] = [a for a in agents if a['Dir'] == 'gascity' and a['Name'] == 'implementation-worker']
    config = dict(default_demand=worker['ScaleCheck'] == '' and worker['WorkQuery'] == '',
                  capped_singleton=worker['MaxActiveSessions'] == 1 and worker['MinActiveSessions'] == 0)
    query = show('internal/config/workquery.go')
    desired = show('cmd/gc/pool_desired_state.go')
    core = dict(
        default_counts_unassigned_ready='it counts\n// ready, unassigned, routed demand' in query,
        desired_state_preserves_owners='new-session demand comes\n// from scale_check, while this function only preserves sessions that already\n// own actionable work.' in desired,
        resume_tier_keeps_in_progress='if wb.Status != "in_progress" && wb.Status != "open" {' in desired
        and 'Resume tier: actionable assigned work beads whose assignee resolves' in desired)
    [rig] = [r for r in city['Rigs'] if r['Name'] == 'gascity']
    survival_config = dict(
        pinned=hashlib.sha256(raw).hexdigest() == CONFIG_SHA,
        no_idle_timeout=worker['IdleTimeout'] == '',
        no_max_session_age=worker['MaxSessionAge'] == '',
        no_sleep_policy=worker['SleepAfterIdle'] == '' and set(rig['SessionSleep'].values()) == {''}
        and set(city['SessionSleep'].values()) == {''},
        claim_holder_recycle_off=city['Session']['ClaimHolderStallTimeout'] == '',
        claimless_recycle_only=city['Session']['ProgressStallTimeout'] == '5m',
        no_chat_session_idle_timeout=city['ChatSessions']['IdleTimeout'] == '')
    config_go = show('internal/config/config.go')
    sleep_go = show('internal/config/session_sleep.go')
    progress_go = show('cmd/gc/session_progress.go')
    reconciler = show('cmd/gc/session_reconciler.go')
    mark = re.search(r'func markProgressStalledClaimedWorkNeedsOperator\(.*?\n}\n', reconciler, re.S)
    update = re.search(r'item\.store\.Update\(item\.bead\.ID, beads\.UpdateOpts\{.*?\n\t\t\}\)', mark.group(0), re.S) if mark else None
    signer = [noatime(path) for path in SIGNER]
    tier = desired[desired.index('// Resume tier: actionable assigned work beads'):desired.index('resumeRequests = append(resumeRequests')]
    build = show('cmd/gc/build_desired_state.go')
    collector = re.search(r'func appendInProgressWorkUnique\(.*?\n}\n', build, re.S)
    readers = subprocess.run(['/usr/bin/git', '-C', CORE, 'grep', '-n', '"needs/operator"', BASE, '--', '*.go',
                              ':(exclude)*_test.go'], env=ENV, capture_output=True, text=True, timeout=60).stdout.splitlines()
    keys = ('ControllerErrorMetadataKey', 'FailureOwnerMetadataKey', 'FailureReasonMetadataKey',
            'FailureSubjectMetadataKey', 'ProgressStallSignatureMetadataKey', 'ProgressLastObservedMetadataKey')
    key_lines = subprocess.run(['/usr/bin/git', '-C', CORE, 'grep', '-n', '-E', 'beadmeta\\.(' + '|'.join(keys) + ')', BASE,
                                '--', 'cmd/gc/*.go', ':(exclude)*_test.go'], env=ENV, capture_output=True, text=True,
                               timeout=60).stdout.splitlines()
    survival_core = dict(
        idle_timeout_empty_disables='// Empty (default) disables idle checking.\n\tIdleTimeout string' in config_go,
        max_age_empty_disables='Empty (default) disables preemptive restarts.' in config_go,
        defer_limit_only_bounds_idle_ladder='AssignedWorkDeferLimit bounds how many consecutive reconciler ticks the\n\t// idle-timeout ladder may defer' in config_go,
        unset_sleep_is_off='\treturn ResolvedSessionSleepPolicy{\n\t\tClass:  class,\n\t\tValue:  SessionSleepOff,\n\t\tSource: SessionSleepSourceLegacyOff,\n\t}\n}' in sleep_go,
        claimless_only='if threshold <= 0 || holdsClaim || !providerHealthy || exempt {\n\t\treturn false' in progress_go,
        claim_holder_needs_threshold='if threshold <= 0 || !holdsClaim || !providerHealthy || exempt || lastProgress.IsZero() {\n\t\treturn false' in progress_go,
        attention_mark_keeps_status_and_assignee=bool(update) and 'Labels: []string{"needs/operator"}' in update.group(0)
        and 'Status' not in update.group(0) and 'Assignee' not in update.group(0),
        collector_keeps_in_progress_by_assignee='listBothTiersForControllerDemand(source.store, beads.ListQuery{Status: "in_progress"})' in build
        and bool(collector) and 'if strings.TrimSpace(b.Assignee) == "" && !isRecoverableUnassignedInProgressPoolWork(cfg, b) {' in collector.group(0)
        and 'Labels' not in collector.group(0) and 'Metadata' not in collector.group(0),
        resume_tier_ignores_labels_and_metadata='wb.Status' in tier and 'wb.Assignee' in tier
        and 'Labels' not in tier and 'Metadata[' not in tier and 'beadmeta.' not in tier,
        needs_operator_has_no_reader=bool(readers) and all(
            'Labels: []string{"needs/operator"},' in line
            or ('build_desired_state.go' in line and 'containsString(work.Labels, "needs/operator")' in line)
            for line in readers),
        mark_metadata_has_no_session_reader=bool(key_lines) and all(
            re.search(r'beadmeta\.\w+:\s', line)
            or 'item.bead.Metadata[beadmeta.ProgressStallSignatureMetadataKey] == signature' in line
            for line in key_lines),
        signer_bead_is_identity_only=all(
            imports_are_stdlib(text) and b'/gascity/bin' not in text and b"'bd'" not in text and b'"bd"' not in text
            and b"'gc'" not in text and b'"gc"' not in text
            and not any(word in text.lower() for word in (b'assignee', b'labels', b'needs/operator', b'progress_stall',
                                                           b'controller_error', b'failure_'))
            and b'bead=_required_identity("bead", arguments.bead, policy.bead_prefix)' in signer[0]
            and b'_identity("bead", request["bead"], policy.bead_prefix)' in signer[1] for text in signer))
    result = dict(config=config, core=core, survival_config=survival_config, survival_core=survival_core)
    result['ok'] = all(v for part in (config, core, survival_config, survival_core) for v in part.values())
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
