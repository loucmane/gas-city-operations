SOURCE_PASS 52666932551053c0a2f7c2e8079dba545583e381463ea9a6014a0750836a84d9
Review-Request-SHA256: 6a0de90d299388da1368e9b3682ea01f2236d07bee4d9552b236b84155f9e11e
candidate=c6b789bbe6ff677dd04336803dbf2c2e017812ba
bead=ga-e0t1.20

must_fix: None.

should_fix: Preserve the complete RED invocation or reproducer in future evidence bundles. [red.log](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.gc/worker-evidence/ga-e0t1.20/r11/red.log:1), lines 1–7, records the actual failure but identifies its script only as stdin. This does not block this patch: the original-source digest and defect agree with the frozen diff.

verified:

1. CLOSE now receives the existing exact started-filename, relative-wrapper, commit and unfinished-record checks. Missing, finalized, malformed and linked records fail closed; a passing hold cannot bypass the explicit exception. See [slots.py](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/slots/slots.py:198), lines 198–235 and 252–260. The 26 malformed-identity cases cover both passing-hold states in [test_slots.py](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/slots/test_slots.py:423), lines 423–456.

2. All three supported held paths receive coordinator-to-own-admission regression coverage; valid CLOSE identity does not override live, partial, between-suspensions or stranded selection. Existing fallback membership and selector logic remain unchanged. Tests: the same `test_slots.py`, lines 405–420 and 459–474; selector: `slots.py`, lines 46–50 and 80–110.

3. Once-only enforcement remains `(commit, wrapper)`, independent of a proposed new job ID. The actual runner predicate is exercised, not replaced with a mock. [jobrunner.py](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-jobrunner/jobrunner.py:392), lines 392–397 and 456–458, establishes enforcement; lines 565–570 establish recording before launch. Regression: `test_slots.py`, lines 477–498.

4. Broken HOLD-1 admission and coordinator passing-hold selection are preserved, while CLOSE independently refuses broken runner state. Regression: `test_slots.py`, lines 501–515.

5. The digest-bound logs report 53 full-suite passes and 36 negative-subset passes. The driver calls real pytest and records source hashes: [test-driver.py](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/.gc/worker-evidence/ga-e0t1.20/r11/test-driver.py:43), lines 43–61. These are recorded worker results, not tests rerun by this reviewer.

6. Verified request, inventory, patch, all inventory-bound artifact digests, all three candidate-source digests and their 0644 modes. The patch contains exactly the three allowed paths. In-memory reverse-diff reconstruction matches all three original-source hashes. [DESIGN.md](/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/gct-oak5-c1-window/DESIGN.md:707), lines 707–727, accurately describes the correction and its boundaries.

Source-only verdict under the report-only evidence workflow. No product execution, tests, Git, Bead, service or lifecycle operations performed. No runner admission, signing, intake, restoration, live acceptance or provider-parity claim; terminal restoration and INSPECT/rebinding remain separate gates.
