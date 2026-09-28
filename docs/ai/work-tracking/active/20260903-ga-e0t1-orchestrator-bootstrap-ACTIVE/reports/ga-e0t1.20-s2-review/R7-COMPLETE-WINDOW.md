# R7 complete operational window after exact recovery

28 September 2026, 19:22 CEST. The original full execution and handover goal
remains incomplete. This packet supersedes R7-WINDOW-HOLD's execution stop only
after its exact, independently reviewed recovery completed. It does not claim
product acceptance, provider parity or handover completion.

## Recovery completed, never replay

Signed recovery candidate 5f51564c1f1a3f7cad2a8fe5e19396deb9a69f45 received two
fresh independent Astra SOURCE_PASS verdicts. The preserved R1 candidate
b6fdabe5442545ff712a8d72d32d6b064a4e7238 received two HOLD verdicts and never ran.
The host runner executed ga-e0t1-20-helper-recover-r1 once at 19:07 CEST.

Result /var/tmp/ga-e0t1.20-helper-archive-20260928-r1/result.json SHA256
b84fad9c6f4ffd9689ba3adec8f38a79e1a62ee130ac469d30aca7d813de54bf:
original_workspace_restored true, actual_host_verified true, host_unchanged
true, worker_launched false. All eight owned phases exited zero with no
timeout, surviving process group or unexpected descendant. All four rigs and
city remain suspended with zero native sessions. The task/parent normalized
pair is unchanged at 7ea9a013e72868853e83e0fe5daeee73824e9c8e7025d5e0609aae8f6d521f48.

The exact unexpected helper now resides at
/var/tmp/ga-e0t1.20-helper-archive-20260928-r1/gc-beads-bd.sh. Its inode 8934271,
device 2096, uid/gid 1000, mode 0755, nlink one, size 312, mtime and content
a7bcaa7cce9261b987bb766fba19db46cc7f4ae8d8b22b6d8059bb884d8788d2
were preserved by non-overwriting atomic rename. Rename necessarily changed
its ctime and parent directory times; these were recorded, not concealed.
All original 8036 workspace entries are restored. No helper deletion or new
workspace allowance occurred. The completed executor/wrapper is historical
and must not run again, including under this later candidate.

Host runner result jobs/done/ga-e0t1-20-helper-recover-r1.json SHA256
e2fc107657f30dd3cf2a8d73c534c33b204ad029140c1197c887fbda86295492.
Parent ga-e0t1 received the result through supported coordination at 19:09 CEST.
No product source was edited and no worker started during recovery.

## Final operational correction and evidence

The first post-recovery full suite preserved 790 passes and one failure in
/tmp/ga-e0t1-r7-post-recovery-full.xml, SHA256
dff544569af1ad97872cec16f30d05626459769d5e57e4141613de5b67fe88c3.
The old directory walker compared complete directory stat before/after its
own readdir, which can change a cold directory's access time. This was an
operational reader defect, not evidence of a changed product candidate.

window_r7.py now emits an O_NOATIME O_NOFOLLOW directory descriptor, compares
its identity before enumeration and both FD/path identities afterward, and
still compares the exact entry list. No metadata comparison is removed. The
fixture reproduces the old atime-only refusal. New executable tests prove the
corrected reader leaves cold directory metadata exact and refuses entry, mode
and inode changes. The historical validator is tested in a read-only fixture;
its source and all failed evidence remain preserved.

Final generator corpus: 796 passed, zero skipped or failed, 35.32 seconds.
/tmp/ga-e0t1-r7-directory-final-full.xml SHA256
3f15c31d3de1f333e3fe8f34d4da4b91abd40d74d5073a8ee84f3faa14fa78ea.
Final materialized contract corpus: 42 passed.
/tmp/ga-e0t1-r7-directory-final-contract.xml SHA256
78b21f00e36575054544f690f35fa14bd5cde59d2e977b465709d5cf19f60dba.
Focused corpus 41 passed, overlapping the full corpus rather than additive.
Its XML SHA256 ce94e3b33ab103808c06057dbe0df1991df67e42c9acabe8ef0bf08685238333.
git diff --check passes. Unit results are not live startup acceptance.

Materialized 89-file R7 package comes from
/tmp/ga-e0t1-r7-window-final-20260928. assembly.json SHA256
30955869bd18d74ee5543cfa7a545a8664b1ba54e6cee463323aec152143ce0c.
startup-validation.py SHA256
f6102dee7f7dd89f89236600aebe8035ebfe0ffde96aa5a4bda49221e4dac9a6.
The source-generation graph retains the actual host, protected-cache, exact
common-Git 44-file exception, native claim, subscription authentication,
pristine source, causal native denial and same-session release checks.

## Exact preserved inputs and scope

R6 predecessor cb4183cccaa35196ec733b427be4cfd9944cab11 and its closed ci-6gwp8
claim/history remain preserved. Its terminal result SHA256 is
dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8.
Its postimage SHA256 is
4da0cc43981ff042e82319f4dd9f2c5c9d8811fed5c716d532cd83c274f690d3.
R7B PREP completed under bd5b64d3fb08863ea6d8d448413172109fb81d46; result SHA256
ecd7512d4ea84340374514acf91a16a27ad33053fd6a1bc68a517eb3be54d24f.
Nothing is installed by PREP. Never repeat WORKTREE, BIND, ROUTE, PREP, task-link
reconciliation, recovery or any consumed prior-window operation.

The new process graph validates the pinned Codex 0.153.4 code-mode host and
at most one exact configured Data Analytics stdio child. Actual argv, executable
and script bytes, ancestry/start/cgroup, prompt and assigned-skills suffix are
verified again before release. The root-owned Node reader preserves every
identity/content check without requiring unsupported O_NOATIME authority.
The exact implicit-cwd sandbox schema and closed literal native-policy-negative
variants remain causal transcript checks, not worker assertions.

Only ga-e0t1.20 through gascity/codex may implement. Its exact base is
c6b789bbe6ff677dd04336803dbf2c2e017812ba in the existing candidate worktree.
The product scope remains C1 DESIGN.md and slots/slots.py plus slots/test_slots.py
for CLOSE self-admission. New worker evidence uses the r7 subtree only. No
Fable/Claude inference, HPFetcher/Blog work, new privilege or signing capability
is introduced. The coordinator has not implemented the product repair.

## Reviewed execution order and dispositions

Two fresh independent reviews must bind the complete signed clean candidate.
Run only through the existing host jobrunner, one unused wrapper at a time,
with result readback between jobs. Clear only each exact understood runner halt
by a preserving non-overwriting move. Never replay a consumed wrapper/root.

1. AMEND-STARTUP-R7 appends only the hash-bound startup references. OBSERVE.
2. PREFLIGHT, STAGE, RESUME. The no-write interval starts at PREFLIGHT.
3. Numbered WATCH for startup, then independent review of the actual startup
   evidence, then RELEASE only after its own exact live checks. No source work
   is authorized by a worker report alone. Failed/ambiguous release contains.
4. Remaining bounded WATCH slots for the candidate. Five-minute startup and
   twenty-minute source-work budget remain. No invented extra poll or nudge.
5. CONTAIN-1, CLOSE-1, an unused WATCH, ADMIT, RESTORE, TERMINAL, INSPECT.
   Existing HOLD and second CONTAIN/CLOSE are bounded recovery paths only,
   never permission to replay an ambiguous mutation.
6. Read terminal/inspection evidence before ending the freeze. Independently
   review the worker candidate before any intake or signed product delivery.

From PREFLIGHT through INSPECT: no workflow.py, coordinator Bead writes,
source edits, unguarded gc, operator tmux pane or coordinator Git in the
candidate workspace. Preserve unrelated service epochs and suspended rigs.
Every genuine stop condition remains. This authorization does not waive an
integrity failure or claim any part of handover complete.
