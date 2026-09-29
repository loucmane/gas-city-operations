# ga-xyqo live outcome — preserved worker failure, recovery PASS

Recorded 2026-09-29 in Stockholm time. The original full provider-independent
execution and handover goal remains active and unchanged.

## Authority

The latest operator approval continues the existing broad completion grant and
the reviewed narrow release-transport bootstrap exception without a new
approval for each hash, job or successful checkpoint. It does not grant new
privilege, relax permission checks or transfer product coding to the coordinator.
Implementation in this attempt was solely by a Gas City Astra high worker.
No Fable or Claude inference, product deployment or protected-project mutation.

## Exact attempt

- Signed package: bebe6bb810b3e963d3a5897c596f57019105d8e1.
- Task ga-xyqo, rig gascity, template gascity/codex, real session ci-0rflg.
- Workspace: /home/loucmane/gas-city-ops-candidate-worktrees/ga-xyqo.
- Real startup and the single release both passed.
- Release result: /var/tmp/ga-xyqo-startup-release-20260929-r1/result.json
  SHA256 5d5aa48ca9d53accc41a2aeef9cd3d76b7db1da2f4db90afc48c93fafa18df39.
- Same-session native nudge nudge-e99d0e54170f, receipt ci-wisp-zmkb,
  transcript acknowledgement verified. No release replay.
- Twelve focused RED failures and partial product changes were preserved.
  GREEN did not complete. No candidate acceptance or useful-execution milestone.

## Failure and diagnosis

The worker recorded STOPPED at its evidence-file mode mismatch. Its newly
created `.gc/worker-evidence/ga-xyqo/r1/digest-history.json` is a regular,
single-link, UID/GID 1000 file of 14474 bytes, mode 0664 instead of required 0600.
The enclosing evidence root is mode 0700. It did not chmod the file or continue.

Read-only inspection of its preserved `refresh.py` identifies the creation:
`history_path.write_text(...)` creates this absent file using the process
creation permissions rather than an explicit 0600 descriptor. Other displayed
evidence files are 0600. This is a worker evidence-creation defect, not failure
of workspace access, startup authentication, source release or native routing.

The partial workspace, bad-mode file and every test record remain unchanged.
No candidate code or refresh script was executed by the coordinator. The normal
candidate inspector is deliberately NOT run against known-invalid evidence;
its permission and scope checks remain unchanged.

## Supported recovery

| Outcome | Completed CEST | Evidence |
| --- | --- | --- |
| CONTAIN-1 PASS | 22:27:46 | Both supported suspension events in the window root |
| CLOSE-1 PASS | 22:34:03 | /var/tmp/ga-xyqo-r1-close-20260929T203258Z/result.json |
| Restore admission PASS | 22:35:41 | window restore-admission-pass.json |
| RESTORE PASS | 22:45:23 | window restore-pass.json |
| TERMINAL integrity PASS | 22:46:49 | /var/tmp/ga-xyqo-terminal-20260929-r1/result.json |

Window root: /var/tmp/ga-xyqo-window-20260929-r1.
CLOSE SHA256 7e72b99efc965b6c648bc029b595d468d7323f5dd699856310dafd4abe009f88.
RESTORE pass SHA256 d81e9a1da9343e5c3bf32e17a91ecfa21ccad7f039e1e8158ded0b9820c8a958.
TERMINAL result SHA256 dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8.

The original city and receipt are restored. All rigs are suspended; zero open
sessions, city tmux sessions and worktree processes were proven. No signals or
tmux-server termination were needed. Full native integrity reports Drifts null,
actual host verification, read-only cache protection, preserved window and exact
terminal/restoration binding. The expected transient controller trace arm
expired without intervention. Runner remains halted after TERMINAL, queue empty.

The first CLOSE submission used an absolute wrapper name instead of the API's
relative name. It refused before queueing. Correcting the argument queued one
job; no operation was repeated.

## Post-terminal workflow and next action

Canonical project context passes. Source readiness is READY for ga-e0t1.
An unnecessary `workflow.py resume` call refused because existing repair
dependencies remain open; this was not a new transaction or source failure.
The supported coordination note on the already-ready context succeeded with
request digest 25dcc0a9c80a5cd309c40f881bac7dea18aef0e42bf2aa2b6ecafa4d24d37c34.
No dependency was removed, closed early or otherwise changed.

Preserve this attempt as failed. Prepare a bounded, independently reviewed
successor that creates evidence securely at creation time and reuses verified
partial source only as unaccepted input. No in-place chmod, inspector waiver,
consumed-window replay or new permissions. Product fixes remain worker-only.
The C1 product repair and actual C1/H1/X/H2/C2/intake/retirement/M13 and terminal
step 5 remain owed; source or recovery PASS cannot satisfy them.

The supported Bead update has now marked ga-xyqo blocked and appended this
failure disposition. Readback changed only status, notes and updated_at;
notes are append-only, assignment stays empty, and all native claim/route
metadata is unchanged. LIVE-BEAD-RECEIPT.json preserves the exact own-field
before/after records. The native session identity remains historical evidence.
