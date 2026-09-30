"""R4 brief r15 (package ga-4xg9-brief-r13): split the reviewed r12 R4 brief verbatim for a readable candidate brief, and add the
pre-window clarifications the r12 reviews and the live claim observation require.

  python3 -B split_r4.py render <out-dir> [<spec-1-id> <spec-2-id>]

Why: `bd show ga-4xg9 --json` is about 39.6K characters (the 21.7K description, notes and the embedded
related ga-fsfg record), over the candidate's inline read limit; the ga-sh3w R3 attempt failed exactly this
way. The operator chose the split for R3 on 2026-09-26; R4 follows the same shape:
- a short task Bead: the r12 head (role, goal, where the mechanisms live), a pointer to the two spec holders
  naming the absolute bd path with one quoted id per command, the r13 clarifications, and the r12 working
  rules; no dependency edge;
- two closed spec holders with the r12 text verbatim: part 1 is the `dispatch` section, part 2 is the
  `evidence-write` section and the acceptance list.
Head + part 1 + part 2 + tail reassemble byte for byte to the r12 brief (ga-cw-first-window R4-brief.md
at 2067a406, sha256 b46fbffe...). The clarifications amend the brief: where they conflict with the spec
text, the clarifications win, and the pointer says so.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

R12_COMMIT = '2067a406'
R12_PATH = ('docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
            'ga-cw-first-window/R4-brief.md')
R12_SHA = 'b46fbffe42f35347ce8e3aaf9c63b34e71953349a47fdeaa87a64d2a4c9a0f46'
OPS = '/home/loucmane/gas-city-ops'
BD = '/home/loucmane/gascity/bin/bd'

CLARIFICATIONS = '''## Pre-window clarifications (part of this description; they win over the spec text)

These answer the r12 reviews and the first live observations; each is binding.

1. **`request()` sites.** R3 is merged at your base (Operations PR 392, merge `8f24ad71`); if
   `aegis_foundation/gate/hooks/delivery.py` is absent at your base, stop with gc.failure_class
   base_without_r3. R3 made the `pretool.py`
   site None-safe. The `tracking.py` PostToolUse site is not generic: a target whose
   `coordination_request()` is `None` goes straight to `record_delivery_event`. `evidence-write` must add
   its own branch there, chosen by the payload (a native `Write` resolved by your evidence-write target),
   before the delivery branch, and a test must show a Write reaches the evidence-write path, not the
   delivery one. The degraded PreToolUse fallback (`degraded_pretooluse_fallback` in `pretool.py`) treats
   only coordination and delivery requests as coordinating; an evidence-write Write must also hard-block
   there, never degrade into the generic Write handling, with a test. Put the new detection inside the
   existing `try`, so a detector exception also counts as coordinating.
2. **Pending dispatch.** Read "every other request at `<W>` keeps refusing while it is pending" as
   "every other `coordinate` action and `reconcile-attachment` refuse while it is pending"; the other
   workflow verbs keep their current behaviour, and nothing in R3's delivery path changes.
   `workflow.py log --root <W> --pending-id <id>` must still run in that state; the remedy depends on it.
3. **Output caps.** The executor caps the `bd ready --limit 0 --json` output at 16 MiB, as
   `workflow_context_recovery.py` does for its reverse-dependency read, and each `bd show`, `agent list`
   and sling JSON output at 1 MiB; it refuses above a cap. The caps are checked after capture, so they
   bound what is accepted, not memory (the 30 s timeouts bound that). A cap refusal after the sling
   leaves the intent pending, like any failed readback.
4. **Bash timeout.** Every gc call that uses the dispatch argv (the `bd show` reads, `bd ready`,
   `agent list`, the sling and the readback) is timed at 30 s; the inherited ownership reads have no
   timeout of their own. Together they can exceed the Bash tool's default timeout. The docs tell the
   caller to pass a Bash timeout of 300000 ms for `coordinate --action dispatch`, and state that a killed
   call is safe because of the `last_sling_at` 60 s guard, except for the residual in item 8. Run the
   sling in its own process group (`start_new_session=True`) and kill the whole group on timeout.
5. **Closed sets and errors.** `dispatch` and `evidence-write` are added to the closed `COMMANDS`
   frozenset in `native_permissions.py`. The executor turns any exception from `_profile()` (for example
   `ValueError`, `DelegationPolicyError` or `OSError`) and a `None` result into a `WorkflowError`. It
   passes the canonical root (the seat, where the profile lives) to `_profile()`: it derives that root
   from the canonical runtime it runs from (the git common directory's parent), never from a hard-coded
   path, and requires it to equal the profile's `canonical_root`; the docs name that root. Reuse the
   gate's existing derivation (`_worktree_and_canonical_root` in `delegation.py`) and give the executor an
   injectable root for tests, so no test reads the live profile.
6. **Operator stuck-state note.** The operator records a stuck dispatch on the primary Bead only after
   the remedy is abandoned: writing it earlier changes the child's stored parent snapshot, so the
   "unrouted and otherwise as recorded" branch could never match again.
7. **Reconcile wording.** Read "No reconcile verb exists for coordination intents today" as "none
   exists for dispatch intents"; `workflow.py reconcile-attachment` exists for `depend` intents only.
8. **Residual double route.** The 60 s re-sling guard holds because every sling call times out after
   30 s. The docs state the residual risk as an invariant: any sling that lands more than 60 s after its
   `last_sling_at` (for example an orphaned or killed sling) could route the child to the same target
   twice.
9. **Observed claim delta (corrects the Readback paragraph and the acceptance bullet "a readback with
   any change beyond `gc.routed_to`, the claim fields (`status`, `assignee`) and `updated_at`").** The
   ga-x7lx window (2026-09-26) observed a pool claim live. Besides `status` (`open` to `in_progress`),
   `assignee` and `updated_at`, a claim also sets `started_at` and the metadata keys `gc.session_id`,
   `gc.session_name` and `gc.work_branch` (Core writes the rig checkout's branch there, a known Core
   defect, ga-l7gz). The accepted claim delta is exactly those fields and keys, added or changed; every
   other field and metadata key must be unchanged, and the acceptance test refuses anything beyond them.
   `status` may change only to `in_progress`. A partial claim delta (any subset of these fields and
   keys) is accepted, since a readback can race the claim.
   The observed route delta matched the brief (`gc.routed_to` added, `updated_at`). Both observations
   were made on a window-prepared Bead that already carried `gc.work_dir` and `gc.check_path`; a
   dispatch child starts with no `gc.*` key, so if a real sling or claim of such a child adds any other
   key, the record stays pending (fail closed) and the docs say the first live dispatch is watched and
   should use a throwaway child.

'''


def r12():
    raw = subprocess.run(['git', '--no-optional-locks', '-C', OPS, 'show', R12_COMMIT + ':' + R12_PATH],
                         check=True, capture_output=True).stdout
    assert hashlib.sha256(raw).hexdigest() == R12_SHA, 'r12 brief digest'
    return raw.decode()


def parts(full):
    def cut(marker):
        assert full.count(marker) == 1, marker
        return full.index(marker)
    a, b, t = cut('## 1. `dispatch`: a new `coordinate` action'), cut('## 2. `evidence-write`: a stationary native Write'), \
        cut('## Working rules')
    head, part1, part2, tail = full[:a], full[a:b], full[b:t], full[t:]
    assert head + part1 + part2 + tail == full
    return head, part1, part2, tail


def spec(n, body, full_sha):
    return (f'R4 spec part {n} of 2 for the ga-fsfg R4 dispatch and evidence-write candidate task. This Bead only\n'
            f'holds text: it is not a work item and is closed. The text below is verbatim from the reviewed r12 R4\n'
            f'brief, whose full SHA-256 is {full_sha}; parts 1 and 2 follow the task brief head in order, as\n'
            f'amended by the task Bead\'s pre-window clarifications, which win where they differ.\n\n' + body)


def pointer(s1, s2):
    return ('## The full specification (read first)\n\n'
            'This description continues in two spec Beads, split only because of its length. Their text is the rest of\n'
            'this description, verbatim from the reviewed r12 brief: the requirements this task must satisfy, incorporated\n'
            'here by reference, as amended by the pre-window clarifications below. Before any work, read both in full, in\n'
            'order, each as its own separate command:\n'
            f'1. `{BD} show "{s1}" --json` (part 1: the `dispatch` action);\n'
            f'2. `{BD} show "{s2}" --json` (part 2: the `evidence-write` class, and the acceptance list).\n'
            'If either read is truncated or fails, stop: set gc.outcome=fail with gc.failure_class spec_unreadable, record\n'
            'which read failed on this Bead, and do not guess the missing text.\n\n')


def render(out, s1='<spec-1>', s2='<spec-2>'):
    full = r12()
    full_sha = hashlib.sha256(full.encode()).hexdigest()
    head, part1, part2, tail = parts(full)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = {'spec-1.md': spec(1, part1, full_sha), 'spec-2.md': spec(2, part2, full_sha),
             'task.md': head + pointer(s1, s2) + CLARIFICATIONS + tail}
    for name, text in files.items():
        (out / name).write_text(text)
        print(name, len(text.encode()), hashlib.sha256(text.encode()).hexdigest())
    return files


if __name__ == '__main__':
    assert sys.argv[1] == 'render'
    render(*sys.argv[2:])
