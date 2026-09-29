# R11 live outcome and reviewed product intake — 2026-09-29 CEST

## Outcome

The real Gas City Astra worker ci-1mh3i completed ga-e0t1.20's three-file CLOSE
self-admission repair. This is a candidate implementation outcome, not full
implementation-worker signing, C1 launch, provider parity or goal completion.

The worker reproduced the original failure, returned 53 full-slot PASS and 36
negative PASS, and appended its completion note once. No coordinator implemented
the product repair. Two independent read-only Astra reviews passed the exact
patch before intake. The worker worktree and all prior evidence remain preserved.

## Live execution and restoration

Frozen signed operational commit: beab8c77c34a9f8aa4d0c41ecd9ac0ee4bb088b4.
Both native operational reviewers passed that exact package.

- Startup: exact claim codex-ci-1mh3i, ChatGPT subscription, scoped workspace,
  foreign-write refusal and actual native signing-policy denial passed. Independent
  startup review passed before release.
- RELEASE acknowledged delivery, not just enqueue. Native shadow receipt
  ci-wisp-0vb8 and nudge nudge-556c91767798 reached provider-nudge-return and the
  exact payload was appended to the same native worker transcript.
- The native release poller PID 3830953 startticks 41667569 was subsequently absent
  in the actual host PID namespace; the releasing unit was inactive. No signal sent.
- The worker finished at about 05:10 CEST. Its later progress-stall metadata reflects
  waiting for coordinator containment after the completion note, not failed coding.
  That native history is retained, not cleared.
- CONTAIN suspended city and gascity only through the reviewed lifecycle.
- CLOSE ended ci-1mh3i at 05:18 CEST and proved zero sessions, city tmux sessions
  and worktree processes. Drain was requested once; the session stayed active
  during the bounded drain wait, then supported session close succeeded. No
  coordinator signal or manual tmux kill was needed. Native close left the task
  open and unassigned with its route and historical session metadata preserved.
- RESTORE applied the exact baseline once. Its known auto-trace-arm wait completed
  at the zero-active-template controller cycle at 05:28:37 CEST. Receipt and
  preservation checks passed; restore completed 05:29:31 CEST.
- TERMINAL passed 05:31:07 CEST: actual host verified, no platform drift, protected
  root cache read-only, accepted restoration and suspension endpoint bound.
- INSPECT passed 05:31:55 CEST: exact three source paths, 13 new evidence files,
  historical evidence and policy preserved, common Git unchanged, no intake or
  execution by the inspector. It reproduced the patch reviewed by both reviewers.

Each distinct job's native runner receipt is preserved under
/home/loucmane/.local/share/gas-city-staging/jobs/done. Earlier HALTED records were
renamed append-forward after their actual results were read. The final INSPECT
HALTED remains in place; no further live job is queued.

## Exact evidence

| Evidence | SHA-256 |
| --- | --- |
| /var/tmp/ga-e0t1.20-startup-release-20260929-r11/result.json | 92d704d51ed28a638f6e63b6c8c52913c5d1de2d6d16caf6328b1bc1c498a2e9 |
| /var/tmp/ga-e0t1.20-r11-close-20260929T031701Z/result.json | 6ed26a4d70b64cbb6d52174a52cd77ffe1c8d952dce9e9d5a00ffc70780e55a7 |
| /var/tmp/ga-e0t1.20-window-20260929-r11/restore-pass.json | d81e9a1da9343e5c3bf32e17a91ecfa21ccad7f039e1e8158ded0b9820c8a958 |
| /var/tmp/ga-e0t1.20-terminal-20260929-r11/result.json | dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8 |
| /var/tmp/ga-e0t1.20-candidate-inspection-20260929-r11/result.json | 468a26ebade2a198d39a8e99b8454180b37829b8efe534d3d02350e26e319c63 |
| /var/tmp/ga-e0t1.20-candidate-inspection-20260929-r11/candidate.patch | 52666932551053c0a2f7c2e8079dba545583e381463ea9a6014a0750836a84d9 |
| Worker r11/source-inventory.json | 730b756cca271cee91f563b784cc77ae0f6f358bddede29a73b11408f4edd716 |
| /tmp/ga-e0t1-r11-product-source-review-20260929.md | 6a0de90d299388da1368e9b3682ea01f2236d07bee4d9552b236b84155f9e11e |

Worker evidence root:
/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.gc/worker-evidence/ga-e0t1.20/r11.
Native poller terminal proof:
/tmp/ga-e0t1-r11-release-poller-terminal-20260929.json.

## Independent review and exact intake

Review A and B both returned SOURCE_PASS for patch
52666932551053c0a2f7c2e8079dba545583e381463ea9a6014a0750836a84d9.
Their candidate commit token is explicitly the immutable worker BASE
c6b789bbe6ff677dd04336803dbf2c2e017812ba, not a falsely claimed committed candidate.
They reviewed the frozen uncommitted patch and manifest. They were not filed as
job-runner admission and do not authorize a live job.

R11-PRODUCT-PATCH.json archives the exact patch as a UTF-8 JSON string; decoding
its patch field reproduces SHA-256 52666932551053c0a2f7c2e8079dba545583e381463ea9a6014a0750836a84d9.
The original R11-PRODUCT.patch remains unchanged on disk and in the worker and
inspection roots. Its required diff-context spaces are data, not source trailing
whitespace; the lossless JSON archive keeps those bytes without a whitespace-gate
exception. No source bytes changed during this evidence-only packaging step.

Native review transcripts in /mnt/c/Users/smoki/.codex/sessions/2026/09/29:
- rollout-2026-09-29T05-25-04-01a0eb31-cd36-75b2-a614-feadd001a055.jsonl
  SHA-256 f59529b1ec77f696a0875bfe8731d059edb62926b271dd13550709cd3653a33e.
- rollout-2026-09-29T05-25-24-01a0eb32-1b41-7952-90ba-82737689bf84.jsonl
  SHA-256 2847a2a2f77f8ca69e4719753545ea7e5bf31493bbec720b4ef9132eee1f0dee.

B's sole non-blocking note asks to preserve the full RED invocation in future
bundles. The original invocation is already present in the preserved native worker
transcript at line 128, call_l1O4CJN8T7xwxBHNPoBnvH4z, timestamp
2026-09-29T03:03:48.603Z:
/home/loucmane/.codex/sessions/2026/09/29/rollout-2026-09-29T04-52-55-01a0eb14-5e61-7662-b048-a45be2876a6d.jsonl
SHA-256 115169fe75ee686d4da5c262fb0c9592f032188fab54dcb8ecbb6140e4c83153.
No RED rerun or product change was made to address that evidence-link note.

After INSPECT, the coordinator verified all three delivery-worktree preimages
equal the worker's original hashes, then applied only the reviewed patch through
apply_patch. The delivery-worktree postimages are byte-identical:
- DESIGN.md afda2b61f57fa3700433e727b4a19a079c5d5ae2d2c44aa7d5a745790a9610bd
- slots/slots.py 4aefce14a0cae55bc3242ad586f3383450ae84e6dade3522d297ede5f2aae5ab
- slots/test_slots.py bbf2add8547d557c7ce22435b375fc17cfe27f0c5c58a3493ba7cc034dc0cf29

Read-only task readback needed host-local Dolt access. The first sandbox read
refused with socket operation not permitted, before mutation; the same read through
the supported host permission path succeeded. No server was started or repaired.

## Next deliverable

Run required final delivery checks on these exact bytes, record the Bead and Aegis
outcome, create a signed checkpoint and deliver under the standing Git/CI gates.
Do not relaunch this completed worker or replay consumed jobs. C1 package generation,
its separately bound live window, handover directions and original step 5 remain
unfinished. All protected projects and unrelated services remain untouched.

## Recording race preserved

The initial supported Aegis evidence log succeeded at 05:39:35 CEST. The child
ga-e0t1.20 outcome note then succeeded and was read back with unchanged open status,
no assignee, route gascity/codex and historical session ci-1mh3i.

The coordinator incorrectly overlapped that child-note write with the parent's
coordination note. The parent operation refused before its Bead mutation because
the parent's embedded child snapshot changed. Exact readback comparison against
snapshot fa376f55b7a345efac87e24902eb11359e6310ba85a3adf7def133e71e8ee5dd
shows only dependencies/3/notes and dependencies/3/updated_at changed. The primary
notes and updated_at are byte-identical to the preimage. This is a diagnosed
pre-Bead-mutation refusal, not security drift or a product failure.

The persisted pending intent is
38f4f7f38b75980a7c0f4c798b489d16255fa6175e1eb27306e36dc21fd01282.
It remains untouched. The installed workflow has no note-intent reconciliation
verb; reconcile-attachment handles depend intents only. No retry, journal edit,
fabricated verified state or direct parent-note workaround was attempted.
Supported logging and delivery checks remain independent of this pending note,
so continue those while preserving the reconciliation obligation. Further ledger
mutations must be serialized, including mutations to embedded child snapshots.
