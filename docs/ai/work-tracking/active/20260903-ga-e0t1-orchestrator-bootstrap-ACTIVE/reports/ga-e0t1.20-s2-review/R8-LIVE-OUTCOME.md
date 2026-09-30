# R8 live outcome — startup proven, release refused, restoration proven

Recorded 2026-09-28 at 23:35 CEST. The original provider-independent execution
and handover goal remains ACTIVE and incomplete. No product repair, candidate
delivery, Claude inference, or handover acceptance is claimed.

## Bound execution

Clean signed operational package c637868cf25442b48418234ac9f1a094ddaac163 had
two independent Astra SOURCE_PASS verdicts under request
4747de189af5ae11412eb5f4b9431817b76e7bd89e699617e0214f43307fa169.
The consumed window is `/var/tmp/ga-e0t1.20-window-20260928-r8`.
AMEND, OBSERVE, PREFLIGHT, STAGE and RESUME passed. One Astra high worker,
ci-sgd80, claimed only ga-e0t1.20 at 23:08:39 CEST.

Both independent startup reviewers returned STARTUP_PASS ci-sgd80 under request
8a200621859db472d19fc2cf38ba01891f2598f5497b73aec0ba7fff3ddf4d6c.
Report SHA256 eea89174ed3b2ec78bc01253c674e12049c044ffc10967a961dbb4b66431079b.
Native reviewer transcripts are 01a0e9db-a153-72d3-91df-c1374e162c23 and
01a0e9db-c188-7683-ac6d-0d4590785c34 in the September 28 Codex session store.
This is startup evidence, not source release authority.

The actual worker transcript is
`/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T23-08-40-01a0e9d9-331e-7943-864b-f638923703d8.jsonl`.
Its reviewed snapshot was owner 1000, mode 0600, one link, 158893 bytes,
SHA256 606cc6668ac00b1655cb9a648ece40cba296848bc461f78a02b3776d208c9147.
The earlier shared creation-policy repair therefore worked for the real client;
no historical transcript was changed. Startup proved the exact base and branch,
ChatGPT subscription without provider overrides, the expected sandbox, positive
workspace write, denied foreign write, and a real pre-execution GPG refusal.
Startup finished before the five-minute limit; end-to-end release did not.
Independent review and coordinator overhead crossed Core's inactivity interval.

## Exact refusal and root cause

RELEASE ran once at 23:17:33 CEST and exited 1 at 23:17:35. Its consumed root is
`/var/tmp/ga-e0t1.20-startup-release-20260928-r8`.
Only inspection and read-only phase evidence exists. `proof.json`,
`nudge-intent.json` and `result.json` are absent. No source-release nudge was sent.
The exception was `startup-validation.py:120: claim metadata differs`.

Core had updated six monitoring fields at 23:14:39 after the deliberately
waiting worker's last observed activity at 23:09:34. Ownership, route and scope
were unchanged. The old frozen metadata referred to closed ci-zcoet; the new
progress-stall envelope correctly referred to ci-sgd80. The signature
bc2c7f90f4b2563aaa35fe4468545c40114057cac6f309dc25d824a961a00ec1 equals
SHA256 of the NUL-joined session ID, task ID, in_progress, assignee and UTC
last-progress string. The host session census independently reports the same
last_active time. Labels remain exactly `["needs/operator"]`.

Deployed Core f45a626213dc5b8d0b52f097d978cca56e506df0,
`cmd/gc/session_reconciler.go:3991-4051`, intentionally records this operator
attention state without recycling the claimed session. The release validator
incorrectly treats these monitoring values as immutable claim identity.
The exact old validator refused correctly under its frozen contract; no
exception was improvised during the live window.

Read-only independent Astra assessment confirms a successor may distinguish
these invariants only with full validation of the complete current-session
envelope, independently observed intentional waiting, and unchanged authority.
The computed signature is consistency evidence, not authentication. Do not
clear the alert, normalize arbitrary metadata, or weaken ownership checks.

## Supported recovery and non-interference

CONTAIN passed at 23:18:53 CEST. CLOSE passed at 23:21:04:
`/var/tmp/ga-e0t1.20-r8-close-20260928T212000Z/result.json` records zero open
sessions, city tmux sessions and workspace processes, with no direct signals
and no tmux-server kill. WATCH-2 independently confirmed zero residue, unchanged
routes/runtime children, and ga-e0t1.20 open and unassigned with its history intact.
ADMIT passed at 23:23:26. RESTORE passed at 23:32:22 after allowing the ordinary
ten-minute diagnostic trace arm to expire; no diagnostic setting was changed.
Its acknowledged revision is a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f.

TERMINAL passed at 23:34:02 CEST with actual host verification, protected cache,
exact accepted restoration, terminal suspension endpoint and native Drifts null.
All jobs have preserved done records and inactive units; all owned phase groups
were reaped. The runner remains halted with an empty queue.

- Terminal root: `/var/tmp/ga-e0t1.20-terminal-20260928-r8`.
- Result SHA256 dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8.
- Observation SHA256 f46054e79167df96ce16d2ae66764a89299c110f15669b27af69defcc86451bf.
- Original city SHA256 bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1.
- Original receipt SHA256 7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba.

After terminal, the unchanged signed strict workspace reader and pristine-startup
validator compared all 8039 prior entries against 8042 current entries. Every
prior source/history/policy entry is unchanged. The only additions are the r8
evidence directory, its startup.json and positive-write.txt. Current image digest
ebc8d19c7a528c012664f648d63e336c964b101641ed4b21d3305badc77afbd2.
Candidate INSPECT is not run: it deliberately requires a nonempty product patch,
and this refused attempt has none. This terminal failure disposition ends the
live freeze without pretending to have a candidate. HPFetcher and Blog are untouched.

## Next bounded correction, not another permission grant

Reproduce this exact current-session stall refusal offline. Preserve the frozen
historical baseline, every non-monitoring field, exact labels, two immediate
claim reads, native transcript/process/permission checks and pristine workspace
proof. Admit only the exact inherited monitoring envelope or the complete
Core-derived current-session envelope with strict chronology, signature and
independent session last-active/wait evidence. Mixed, missing, extra, foreign,
malformed or future fields and any ownership change must still refuse. Keep
whole-task equality across the two immediate release reads conservative.

Bind recovered ci-sgd80 history and all r8 files in a fresh successor; never
replay this release or any completed stage/restore. Check the complete output
contract, including private modes for worker-created evidence, before dispatch.
Use focused regression and one consolidated operational corpus, then two exact
independent source reviews. Product implementation remains Gas City worker-only.
No deferred workflow-improvement initiative is added as a prerequisite.
