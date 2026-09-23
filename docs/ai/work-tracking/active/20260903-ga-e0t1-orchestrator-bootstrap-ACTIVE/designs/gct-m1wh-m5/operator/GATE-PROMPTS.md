# M5 in-window gate prompts (templates)

Fill in `{COMMIT}`, `{EXTRACT}`, `{PACKAGE}` and `{BASELINE}` (the pinned `BASELINE_SHA`) from `gate_extract.py`, then launch both reviewers in
parallel through the Agent tool (`aegis-reviewer`). Put only the candidate token on the first line;
no path token is used for this Operations checkout.

**Outcome handling (coordinator).**
- Two passes: write both drafts with the Write tool into the staging directory
  `/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922`, never into the
  package checkout. Then run `record_review.py record <KIND>`.
  `operator/M5-EXECUTE.sh` sees `q/<kind>.json` and continues.
- Any HOLD, a refusal or a missing verdict: create
  `/home/loucmane/.local/share/gas-city-staging/gct-m1wh-metadata-20260922/HOLD-<kind>.json`, for
  example `HOLD-source-pass.json`. The wrapper stops and prints the recovery for that point.
- Never write a HOLD marker and a pass record for the same gate.
- From `prepare` until `restore-accepted`, write nothing into the package checkout: no commit,
  no aegis or workflow log, no draft. The wrapper stops at any tracked or unignored change.
  Staging files are fine. Bead notes and every gc call wait until after restore-accepted (the
  quiescent-window rule).

- Q = `/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5/q`
- PKG = `/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5`

## SOURCE_PASS

```
candidate={COMMIT}

TIME-CRITICAL: the M5 executor's 15-minute window is running. Use at most 8 tool calls and finish
within 3 minutes. Read-only.

Gate: SOURCE_PASS for the prepared M5 package (Bead ga-0t04). Package digest (sha256 of
Q/prepared.json, computed by the coordinator): {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5/q
PKG = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-m1wh-m5
Coordinator extract (a claim): {EXTRACT}

1. Read the extract. It must show all of the following:
   - flags preparation_only true, live_acceptance false, timer_paused true and native_launched false;
   - accepted_recovery_sha256 equal to baseline_pin {BASELINE};
   - broker_receipt_sha256 equal to candidate_receipt_sha;
   - sources_count 13 and sources_equal_expected true;
   - release_id template-pr69-opus55-metadata-m5-20260923;
   - last_repository template-pr69-authority at 28539934fa742056e0a65710d5638ff559a21175;
   - counts 685/49/23;
   - every changed_inputs value true;
   - python_test_inputs 0;
   - evidence reports/m5/t;
   - closure_exists and all three paused_binds_* true;
   - stop_returncode 0;
   - manifest_file_sha256 equal to prepared_manifest_file_sha256.
2. Confirm in the originals with Grep -o (the files are single-line JSON):
   - Q/prepared.json has "preparation_only":true, "native_launched":false and
     "accepted_recovery_sha256":"{BASELINE}";
   - Q/manifest.json has "release_id":"template-pr69-opus55-metadata-m5-20260923" and the authority
     repository at 28539934, and no match for python3\.12/test/.
3. Confirm that PKG/source-pins.json lists the six package sources the extract expects.

Output: the first line is SOURCE_PASS or HOLD. Then one paragraph that restates the package digest
and every fact you confirmed directly, and notes the gate audit reason
read_only_reviewer_delegation.
```

## PAIRING_PASS

```
candidate={COMMIT}

TIME-CRITICAL: the M5 executor window is running. Use at most 8 tool calls and finish within
3 minutes. Read-only.

Gate: PAIRING_PASS after the native metadata-only dry-run observation (Bead ga-0t04). Package
digest {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5/q
Coordinator extract (a claim): {EXTRACT}

1. Read the extract. It must show all of the following:
   - observe phase observe, exit_code 0, terminal_pidfd true, errors [], record_error null and
     stderr "";
   - argv exactly [gc, platform, adopt, --metadata-only, --dry-run, --manifest, Q/manifest.json],
     where gc is /home/loucmane/gascity/bin/gc;
   - mutate_only_allowed true: exactly the four MUTATE actions, each once on its own target.
     write-previous-manifest-backup and write-previous-receipt-backup write under reports/m5/b;
     publish-manifest and write-activation-receipt write under
     /home/loucmane/gascity/city/.gc/platform;
   - unparsed_plan_lines empty;
   - after_matches true and observe_baseline_is_window true;
   - window_deadline_equals_prepared true and window_closure_equals_preparation true;
   - no_later_records true;
   - probe limit 36 in the bindings.
2. Read Q/observe-result.json (a small single line; if the line is truncated, use Grep -o) and
   confirm:
   - the plan header names release template-pr69-opus55-metadata-m5-20260923;
   - every step other than the four MUTATE steps is CHECK.
3. Read Q/after-observation.json (tiny) and confirm ok true and complete_preservation true.

Output: the first line is PAIRING_PASS or HOLD. Then one paragraph that restates the package
digest, the observation_result_sha256 and window_sha256 from the bindings, and what you confirmed
directly. Note the gate audit reason read_only_reviewer_delegation.
```

## COMMIT_PASS (no window deadline, but before the cache horizon)

```
candidate={COMMIT}

Gate: COMMIT_PASS after the native metadata commit and verify (Bead ga-0t04). There is no window deadline, but restore-accepted must run before the cache-renewal horizon,
so be thorough. Read-only. Package digest {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m5/q
Coordinator extract (a claim): {EXTRACT}

Confirm from the extract and from the originals:
1. Q/committed-acceptance.json shows:
   - ok true and lease_expired true;
   - package_sha256 equal to the package digest;
   - commit_result_sha256 binding Q/commit-result.json;
   - manifest_sha256, receipt_sha256, canonical_file_sha256 and receipt_file_sha256 present.
2. Q/commit-result.json is phase commit, exit_code 0, errors [], record_error null and stderr "",
   with argv `gc platform adopt --metadata-only --apply --manifest Q/manifest.json`.
3. The live files hash to the acceptance's file digests: /home/loucmane/gascity/city/.gc/platform/
   install-manifest.json to canonical_file_sha256, and install-receipt.json to receipt_file_sha256.
   The live manifest must equal Q/manifest.json (live_manifest_equals_q_manifest).
4. No restore record exists yet (restore_absent true).
5. Check for any sign of a partial or duplicated commit: probe, probe2 and commit records are each
   exactly one consumed/result pair.

Output: the first line is COMMIT_PASS or HOLD. Then an assessment paragraph that restates the
package and acceptance digests. Note the gate audit reason read_only_reviewer_delegation.
```
