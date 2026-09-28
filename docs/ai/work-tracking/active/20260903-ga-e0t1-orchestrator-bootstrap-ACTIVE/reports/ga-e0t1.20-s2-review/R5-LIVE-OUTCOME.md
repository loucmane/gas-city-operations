# R5 worker window — contained startup refusal, restoration PASS

2026-09-28 Europe/Stockholm. Same goal and ga-e0t1.20. No product acceptance.

## Delivered and reviewed

Signed operational candidate ff1212c23576ff3f2da13ba4ddf703c18ce9bc68.
Both fresh independent Astra reviewers returned SOURCE_PASS. Request:
`/tmp/ga-e0t1-20-r5-full-window-reviews-20260928/request.md`,
SHA-256 cf3caf9a7b74f0285e7e51caaf70dc6587471dda8674bcfd6eb99d2bcd58b173.
Native envelopes are preserved and filed by the existing runner:
codex-01a0e80f-4204-7363-8a24-3b8436047410.json and
codex-01a0e80f-695f-7d63-9a5a-3502e877865c.json.
Review B's nonblocking suggestion is preserved: add persistent-torn-read timeout
and invalid-subsequent-sample cases to the generated suspension-loop tests.
Do not make this deferred suggestion a new execution prerequisite.

## Actual outcomes in CEST

- 14:54:28 AMEND passed: one exact startup note appended; no route, claim or configuration change.
- 14:55:54 OBSERVE passed: actual host verified, protected cache read-only, no native drift.
- 14:57:36 PREFLIGHT passed against original workspace and zero-residue state.
- 15:00:24 STAGE passed with the native-prepared isolated configuration and receipt.
- 15:01:36 RESUME passed. Only gascity/codex was eligible.
- 15:02:24 WATCH passed: one actual session ci-rks41, correct task claim, exact workspace,
  Astra high, unchanged routes/runtime directories, no extra session.
- The actual worker claimed and read the Bead, verified the probe digest, then ran
  worker-startup.py in its ordinary sandbox. It refused at subscription identity,
  appended STOPPED through the supported literal control prefix, and waited.
  No source release, product edit, test, signing, staging, commit or task close.
- 15:04:00 CONTAIN passed. City and rig suspended through supported lifecycle.
- 15:05:59 CLOSE passed: ci-rks41 closed, zero native sessions, zero city tmux sessions,
  zero candidate-workspace processes; no forced signal or tmux-server kill.
- 15:07:06 restoration ADMIT passed.
- 15:17:34 RESTORE passed. The automatic diagnostic trace arm expired at
  15:16:07.884 CEST; restoration waited under its existing bounded contract.
  The waiting cycles had the exact restored revision and no decisions/mutations.
- 15:19:11 TERMINAL passed: exact accepted restoration, actual host, suspended endpoint,
  protected cache, full native platform integrity with no drifts.
  The observer's worker_launched=false means that observer launched none;
  this window DID launch the one worker above.

Completed job records are in
`/home/loucmane/.local/share/gas-city-staging/jobs/done/ga-e0t1-20-r5-*.json`.
Every consumed root and latch remains preserved. No replay.

## Exact evidence

Terminal result:
`/var/tmp/ga-e0t1.20-terminal-20260928-r5/result.json`
SHA-256 dd9a145c6eaf29b03fe117c18d4e1a20d1537ba6a64919efe44531ef554a1ff8.

Close result:
`/var/tmp/ga-e0t1.20-r5-close-20260928T130452Z/result.json`
SHA-256 53b7501005e7f48722f022e023995ba6c9c8b83f3e7adcfa4c6d9e6089da46ea.

Restore result:
`/var/tmp/ga-e0t1.20-window-20260928-r5/restore-pass.json`
SHA-256 d81e9a1da9343e5c3bf32e17a91ecfa21ccad7f039e1e8158ded0b9820c8a958.

Native worker rollout:
`/home/loucmane/.codex/sessions/2026/09/28/rollout-2026-09-28T15-01-42-01a0e81b-5b23-7db2-820c-0aadd1db996e.jsonl`
SHA-256 0f66ee523871e9b67f4b0020b55b8774a23a8affd8987abb0ddf692eac15f2da.

## Post-terminal source proof

Read-only harness `/tmp/ga-e0t1-20-r5-noninterference-20260928.py`
uses the exact pinned reviewed inventory functions, no Git or product execution.
Two complete scans match: original 8015 entries unchanged; current 8032 entries
are exactly the original plus 17 authorized Core runtime entries. No startup
evidence directory or product edits. Inventory SHA-256:
e187fb930887244879f81662113b326d731e1c245467976fafee8ebff2f7900f.
The success-only candidate INSPECT job was not run because no product candidate
exists. This is non-interference proof, not candidate acceptance.

## Specific diagnosed defect and smallest next action

The startup probe concatenates stdout/stderr and demands exact equality with
Logged in using ChatGPT. A read-only status reproduction using the same pinned
CLI and Linux CODEX_HOME returned exit 0, exactly one subscription line, and:
WARNING: proceeding, even though we could not create PATH aliases: Read-only file system (os error 30)

No API/provider override was present in the actual worker before this probe;
its preceding override check passed. The diagnostic prints no credentials or
unknown text. Persistent authentication/configuration was not modified.
The actual worker probe did not preserve its captured status streams, so the
later reproduction is not mislabeled as that missing raw worker capture.
It reproduces the exact overly-strict parser failure with a successful
subscription result under filesystem write protection.

Next: narrow operational-probe correction to accept only that exact known local
filesystem warning alongside the successful exact subscription identity.
Retain exit-code, single identity, pinned CLI and all environment, sandbox,
ownership, native permission and signing-negative checks. Unknown warnings,
API identity, mixed identities and nonzero status must still refuse.
Require tests and independent review; do not rerun R5 or change credentials.
Preserve all completion evidence when preparing the append-forward successor.
