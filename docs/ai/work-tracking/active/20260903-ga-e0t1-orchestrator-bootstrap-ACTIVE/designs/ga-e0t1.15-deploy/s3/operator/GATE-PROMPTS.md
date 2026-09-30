# M6 in-window gate prompts (ga-e0t1.15 S3)

These are the M5 gate prompts, rebound to M6. Fill in `{COMMIT}`, `{EXTRACT}`, `{PACKAGE}` and
`{BASELINE}` from `gate_extract.py`. Then launch both reviewers in parallel through the Agent tool
(`aegis-reviewer`).
- The prompt must contain the candidate token exactly once and no path binding token.
- Ask for "the verdict word followed by the full commit"; never write a second candidate token.

**Outcome handling (coordinator).**
- **Two passes:** write both drafts with the Write tool into the staging directory
  `/home/loucmane/.local/share/gas-city-staging/ga-e0t1.15-s3`, never into the package checkout.
  Each draft is `{reviewer_id, verdict, bindings, assessment}`, with the bindings exactly as
  `record_review.py bindings <KIND>` prints them. Then run `record_review.py record <KIND> <a> <b>`.
- **Any HOLD, refusal or missing verdict:** stop at that gate and take the exit for that point:
  - SOURCE_PASS gate (after `prepare`, before `pause`; no `window.json` yet):
    `recover-preparation <sha256 of q/preparation-pause-intent.json>`.
  - A `pause` failure: `recover-pause` if `q/pause-consumed.json` exists and `window.json` does not;
    otherwise the recovery the executor names.
  - PAIRING_PASS gate, or anywhere after `window.json` and before `paired` launches: `restore-preapply`.
  - After `paired`: never restore-preapply; inspect the commit evidence and stop.
- **Quiescence:** from the capture until `restore-accepted`, make no tracked or unignored write in the
  package checkout, run no gc or `workflow.py`, write no Bead note, and run no git command at all in
  the canonical Template, any of its linked worktrees (the PR 71, PR 69 and PR 61 authorities and every
  review worktree), the Core rig, the codex authorities or the packs repository. The baseline pins
  their common Git directories exactly.
- **Timing:** start `observe` only with more than 180 s of window left, and `paired` only with more
  than 300 s. The executor's own deadline checks remain authoritative.

- Q = `/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m6/q`
- PKG = `/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1.15-deploy/s3`

## SOURCE_PASS

```
candidate={COMMIT}

TIME-CRITICAL: the M6 executor's 15-minute window is running. Use at most 8 tool calls and finish
within 3 minutes. Read-only.

Gate: SOURCE_PASS for the prepared M6 package (Bead ga-e0t1.15). Package digest (sha256 of
Q/prepared.json, computed by the coordinator): {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m6/q
PKG = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/ga-e0t1.15-deploy/s3
Coordinator extract (a claim): {EXTRACT}

1. Read the extract. It must show:
   - flags preparation_only true, live_acceptance false, timer_paused true, native_launched false;
   - accepted_recovery_sha256 equal to baseline_pin {BASELINE};
   - broker_receipt_sha256 equal to candidate_receipt_sha (f55fed69...);
   - sources_count 13 and sources_equal_expected true;
   - release_id template-pr71-core-seq14-metadata-m6-20260925;
   - previous_manifest 2d7eadce...;
   - last_repository template-pr71-authority at cfd353f30f465cdf67bbd41fab48812fe5b9617e;
   - pr69_authority_absent true;
   - counts 687/49/23;
   - every changed_inputs value true;
   - core source /var/tmp/ga-e0t1.15-build-20260925/gc-a with sha b2760ea4...;
   - activation expected_commit 9faeabc2... and previous_commit 796d9a7a...;
   - writer sha b2760ea4...;
   - cache_sha256 4b284f67...;
   - evidence ending in reports/m6/t;
   - closure_exists and all three paused_binds_* true;
   - stop_returncode 0;
   - manifest_file_sha256 equal to prepared_manifest_file_sha256.
2. Confirm in the originals with Grep -o (single-line JSON):
   - Q/prepared.json has "preparation_only":true, "native_launched":false and
     "accepted_recovery_sha256":"{BASELINE}";
   - Q/manifest.json has "release_id":"template-pr71-core-seq14-metadata-m6-20260925", the
     authority repository at cfd353f3, and no "template-pr69-authority".
3. Confirm that PKG/source-pins.json lists the six package sources the extract expects.

Output: the first line is the verdict word (SOURCE_PASS or HOLD) followed by the full commit. Then
one paragraph that restates the package digest and every fact you confirmed directly.
```

## PAIRING_PASS

```
candidate={COMMIT}

TIME-CRITICAL: the M6 executor window is running. Use at most 8 tool calls and finish within
3 minutes. Read-only.

Gate: PAIRING_PASS after the native metadata-only dry-run observation (Bead ga-e0t1.15). Package
digest {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m6/q
Coordinator extract (a claim): {EXTRACT}

1. Read the extract. It must show:
   - observe phase observe, exit_code 0, terminal_pidfd true, errors [], record_error null and
     stderr "";
   - argv exactly [gc, platform, adopt, --metadata-only, --dry-run, --manifest, Q/manifest.json],
     where gc is /home/loucmane/gascity/bin/gc;
   - mutate_only_allowed true: exactly the four MUTATE actions, each once on its own target.
     The two backups write under reports/m6/b; publish-manifest and write-activation-receipt write
     under /home/loucmane/gascity/city/.gc/platform;
   - unparsed_plan_lines empty;
   - after_matches true and observe_baseline_is_window true;
   - window_deadline_equals_prepared and window_closure_equals_preparation true;
   - no_later_records true;
   - probe limit 36 in the bindings.
2. Read Q/observe-result.json (use Grep -o if the line is long) and confirm:
   - the plan header names release template-pr71-core-seq14-metadata-m6-20260925;
   - every step other than the four MUTATE steps is CHECK.
3. Read Q/after-observation.json and confirm ok true and complete_preservation true.

Output: the first line is the verdict word (PAIRING_PASS or HOLD) followed by the full commit. Then
one paragraph that restates the package digest, observation_result_sha256 and window_sha256 from the
bindings, and what you confirmed directly.
```

## COMMIT_PASS (no window deadline)

```
candidate={COMMIT}

Gate: COMMIT_PASS after the native metadata commit and verify (Bead ga-e0t1.15). There is no window
deadline, so be thorough. Read-only. Package digest {PACKAGE}.
Q = /home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap/reports/m6/q
Coordinator extract (a claim): {EXTRACT}

Confirm from the extract and the originals:
1. Q/committed-acceptance.json shows:
   - ok true and lease_expired true;
   - package_sha256 equal to the package digest;
   - commit_result_sha256 binding Q/commit-result.json;
   - manifest_sha256, receipt_sha256, canonical_file_sha256 and receipt_file_sha256 present.
2. Q/commit-result.json is phase commit, exit_code 0, errors [], record_error null and stderr "",
   with argv `gc platform adopt --metadata-only --apply --manifest Q/manifest.json`.
3. The live /home/loucmane/gascity/city/.gc/platform/install-manifest.json hashes to
   canonical_file_sha256, and install-receipt.json to receipt_file_sha256. The live manifest equals
   Q/manifest.json.
4. No restore record exists yet.
5. The probe, probe2 and commit records are each exactly one consumed/result pair.

Output: the first line is the verdict word (COMMIT_PASS or HOLD) followed by the full commit. Then an
assessment paragraph that restates the package and acceptance digests.
```
