# R7 live outcome and bounded next action

28 September 2026, 20:00 CEST. The full provider-independent execution and
handover goal remains incomplete. This is a failed source-release attempt with
verified restoration, not product acceptance. No product implementation occurred.

## Exact candidate and completed sequence

Signed package HEAD: 1c4608709f51097767394573aff719682fa0e8b0.
Assembly SHA256: 30955869bd18d74ee5543cfa7a545a8664b1ba54e6cee463323aec152143ce0c.
Both independent Astra reviewers returned SOURCE_PASS for this exact candidate.
The preserved full generator and materialized suites are 796 and 42 passes;
they are not live acceptance and need not be rerun merely to record this outcome.

The host jobrunner completed AMEND-STARTUP, OBSERVE, PREFLIGHT, STAGE and RESUME.
Native session ci-zcoet, named codex-ci-zcoet, started at 19:36:24 CEST. The
worker used gpt-6-astra at high effort, completed startup at 19:37:13, and waited.
Startup independently passed: exact claim/base/branch, workspace positive and
foreign-write negative, ChatGPT subscription with no provider overrides, and a
causally matched native refusal of direct GPG. Seven startup tool calls were
observed; no source edit or delegation occurred.

Startup report SHA256:
03c8af6ecc7bf28e1af31319047647578bc52a01042a94fafb820cdb8110f074.
Report lives in the worker workspace under
.gc/worker-evidence/ga-e0t1.20/r7/startup.json.

RELEASE refused at 19:42:07 before creating proof.json, nudge-intent.json or
result.json. No source-work permission was sent. Independent startup review
finished around 19:41, so review and release extended beyond five minutes from
session creation even though worker startup itself finished in 49 seconds.
Preserve this timing distinction; do not claim a five-minute end-to-end release.

## Exact refusal and cause

Log:
/home/loucmane/.local/share/gas-city-staging/ga-e0t1-20-astra-window/release-20260928T174205Z.txt.
runtime-process-r7.py reached candidate-inspect.py file_bytes while reading the
actual transcript held open by the worker. It refused with
`candidate file authority or bound`.

Transcript:
/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T19-36-26-01a0e916-e320-7cc2-bec4-d6150af37512.jsonl.
Observed owner/group 1000, mode 0664, nlink one, device 2096, inode 4059323,
size 142427. The existing reader correctly forbids group/other write.
Actual-host process readback found Core PID 2800348 Umask 0002 and jobrunner
PID 2812303 Umask 0022. This is an inherited worker-creation-policy mismatch,
not evidence that the worker edited the transcript or that the binary changed.
No permission was relaxed and the preserved transcript was not chmodded.

## Containment and restoration proven

CONTAIN passed, then supported CLOSE ended ci-zcoet without direct signals or
tmux-server killing. Post-close WATCH proved no native sessions, no city tmux
sessions, no workspace processes, and preserved routes/directories. The task
is open and unassigned. Native progress-stall history for ci-zcoet remains
preserved; it is not rewritten as a success.

ADMIT passed. RESTORE ran once from 19:49:18 to 19:57:06 CEST. The baseline
reload was applied; the known auto-trace arm was waited out using the existing
bounded read-only policy. TERMINAL passed at 19:58:47 CEST with real host
verification, protected-cache read-only verification, no platform drifts,
city and all four rigs suspended, and zero native sessions/running agents.
Core 2800348, broker 2940285 and signer 2310 retain their original epochs and
zero restarts. No success-only candidate intake/INSPECT is claimed or executed.

Evidence digests:

- /var/tmp/ga-e0t1.20-r7-close-20260928T174426Z/result.json:
  15a5a5911abe86bc55a7291b3cea366e8eda9a515353b26968cf8030aa6520d0
- /var/tmp/ga-e0t1.20-r7-watch-20260928T174647Z/result.json:
  7d3760671cf808c0e92ef1eb8739601e383cc8c73440941676bfd13c9eb12b6f
- /var/tmp/ga-e0t1.20-window-20260928-r7/restore-pass.json:
  d81e9a1da9343e5c3bf32e17a91ecfa21ccad7f039e1e8158ded0b9820c8a958
- /var/tmp/ga-e0t1.20-terminal-20260928-r7/result.json:
  dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8
- /var/tmp/ga-e0t1.20-terminal-20260928-r7/preservation.json:
  02c43c416b8e88877865422b50aaa7f22f4dca9b620bc901b4d553e76cbac305

The terminal result digest equals an earlier result because its generic JSON
fields are byte-identical; the R7 directory, job binding and observed snapshots
establish this attempt's identity. Do not substitute the R6 record for R7.

All three product hashes remain their exact initial values:
DESIGN.md 15da64571068451f19b742883a9c6bd662b726412b9d0678d8a4b2b4b1f32a4b;
slots.py 2b42c4687385121cd6ca3defe31f087d073b9a666dfa7f7f4e0a01969201ff68;
test_slots.py 3e97f3422037ae41bbc1690baf12e3ce9eb2da5cc9e566fed9493a55729de2f7.

## Decision and next deliverable, not another blind retry

The bounded mechanism assessment is concluded: tighten file creation at the
single worker's provider launch. Do not relax the reader, chmod failed evidence,
alter the supervisor service or restart it, or switch to seat-direct coding.

Independent read-only Astra assessment by aegis_window_r7_b verified against
pinned Core f45a626213dc5b8d0b52f097d978cca56e506df0, not checkout HEAD:

- No dedicated per-worker umask setting exists.
- Provider command shell-wrapper composition and explicit path_check are
  supported in internal/config/provider.go at 92 and 267.
- The proposed composition is `/usr/bin/sh -c 'umask 0022 && exec /home/loucmane/gascity/bin/codex "$@"' --`.
  Preserve codex-managed inheritance, arguments/options and the Codex path_check.
  Bind an equivalent resume_command if resume remains supported.
- Do not substitute agent start_command; it bypasses provider resolution.
  pre_start runs in a separate shell and cannot propagate its umask.
- Command changes alter the behavioral fingerprint and configuration revision.
  Existing R7B profile bodies do not include gascity/codex; preserve them and
  regenerate the permission revision and receipt self-digest through the
  reviewed preparation path. No full managed-profile/signing claim follows.

Next package must first test the exact short/long-prompt launch composition,
eventual executable/argv identity, new transcript permissions, unchanged negative
permission checks, and every remaining RELEASE predicate using real R7 evidence.
Then obtain consolidated independent review before any live successor window.
Use fresh append-forward evidence roots and preserve this consumed R7 root.
No package construction or live launch for this correction has happened yet.

Standing authorization covers in-scope corrected packages after verified
restoration; a new hash is not a new operator-approval boundary. Actual new
privilege, uncertain mutation, security drift and other standing stops remain.
No Fable/Claude inference, HPFetcher/Blog work, cleanup or unrelated change.

## Append-forward complete-predicate assessment, 20:13 CEST

The preliminary launch-wrapper recommendation above is NOT execution-ready.
The full remaining-predicate audit found the next concrete refusal before any
new worker run: existing .codex/rules/default.rules is also mode 0664, uid/gid
1000, one link, 852 bytes, exact pinned SHA256
3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516.
startup-release.py line 120 would reject it through the same strict reader.
New-process umask cannot change an existing file. Parents .codex/rules and
sessions/2026/09 and sessions/2026/09/28 are mode 0775. The current reader
checks final-file authority and resolved paths, not writable parent authority;
this is a separate integrity limitation rather than an observed R7 replacement.
Readback found no access/default ACL xattrs on these Codex paths.

Independent A otherwise matched preserved schema, claim, note, causal native
denial, transcript identity, prompt/skills/argv, 8039-entry pristine workspace,
local rules, generated hook, client input hashes and absent foreign marker.
Transcript digest 70d7843a77f3b8184730e2a3ab7a4bab5556ae8e966ef595bda51cc33fc3f50d.
Its last task_complete record preceded release; no concurrent append was
observed. A future append during read or partial JSONL line correctly refuses.
The existing later runtime revalidation does not recheck transcript FD/content;
do not claim otherwise or substitute this audit for the live gate.

The disposable shell test preserved at
/tmp/ga-e0t1-r8-launch-mask-20260928/test_launch_mask.py
SHA256 4dde6f38246ef1bb7ecae1d895107c9ec1b34f3e11b90848a0d283f4fd716d13
produced 5 passes and 4 short-prompt PID failures. Its original XML is
results.xml SHA256 ba03471a80139ab42220041801de2d60bb262b823c761a79a4ba36f5e00f20d3.
Reviewer B corrected the earlier unconditional pane-PID claim: pinned Core
passes one command string to tmux, short prompts lack outer exec, and long
prompts still depend on the outer shell optimization. No generic config-only
wrapper guarantee was established. Do not relaunch using that unproven claim.

A narrower configuration architecture was then tested entirely in disposable
directories, without invoking Codex: owner-only default creation ACLs produce
0700 future directories and 0600 future files despite inherited masks 0002,
0022 or 0077, for both requested file modes 0666 and 0600. All six cases passed
in test_private_creation_policy.py and private-creation-results.xml under the
same temporary evidence root. Kernel ACL APIs are available without installing
packages. This would avoid changing Core, argv, provider identity or epochs.

The first generic default-ACL fixture produced 0755/0644 and is preserved as
feasibility evidence ONLY: it is not the proposed policy, because a default ACL
granting group/other reads could defeat an intentional umask 0077. The owner-only
variant adds no group or other access.

Concrete decision proposed for independent review and bounded ACL authority:
normalize only the existing default.rules file and the exact sessions/rules
parent chains to owner-only access, with inherited owner-only defaults for
future files/directories. Preserve contents, ownership, all historical
transcripts and all unrelated paths. Require preimage/ACL backup, identity-bound
no-symlink operations, explicit expected ctime changes, stable host/session
checks, owner-only rollback and readback; no timestamp falsification. Permission
and default-ACL adoption has NOT been authorized by these fixture results or
executed. Current production state remains the verified restored R7 baseline.

This completes the bounded mechanism assessment. Do not resume the old wrapper
approach or start another live window before the consolidated disposition.

Independent reviewer B confirmed the owner-only alternative is feasible, not
live acceptance. The current strict reader accepts 0600 without relaxing any
owner, link, alias, size or stable-read check. The policy does not change argv
or ancestry. It is account-directory-wide creation policy, not confinement
against the owning UID: rename-in, later chmod or ACL replacement still require
strict checks. Do not generalize the tested masks to arbitrary owner-bit masks.

Before adoption, prove all affected creators are quiescent or serialized, not
just Gas City workers. Do not interrupt unrelated sessions. No recursive home
migration is proposed. Preserve every existing transcript's bytes and metadata;
enumerate exact target directories and the one rules file. Rollback requires
exact postimage comparison and handling any newly inherited directory defaults;
removing only the parent default is insufficient. Do not automatically widen
permissions back to group-writable modes. Resolve this bounded shared-directory
permission disposition explicitly before a live installer or worker retry.
