# ga-e0t1.20 — preparation complete, worker not released

Checkpoint: 2026-09-27 23:03 CEST. The original provider-independent execution
and bidirectional handover goal remains active and unchanged. This is the
preparation for a narrow Gas City Astra source repair, not provider-parity proof.

## Completed outcomes — do not repeat

- Signed package aa2522b9b33e88775d0542f356f6f5f05a86b0cf received two fresh
  independent request-bound Astra SOURCE_PASS reviews.
- WORKTREE job ga-e0t1-20-s1-worktree-r3 ran at 22:57:47–22:57:49 CEST.
  Its wrapper reported WORKTREE PASS and the job is inactive, exit 0.
- PREP job ga-e0t1-20-s1-prep-r3 ran at 22:59:05–22:59:06 CEST.
  Its wrapper reported PREP PASS and the job is inactive, exit 0.
- Both outcomes were appended to the authoritative ga-e0t1 Bead. Both HALTED
  latches were preserved as the jobs' done/*.halted-cleared.json records after
  checking their final results, wrapper logs, inactive units and empty queue.
- No worker, model inference, route, rig resume, live receipt/config installation
  or product-source edit occurred. ga-e0t1.20 is still open, unassigned/unrouted.

## Exact workspace and image

Workspace: /home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20
Branch: codex/ga-e0t1.20-c1-close-admission
Signed source base: c6b789bbe6ff677dd04336803dbf2c2e017812ba
Admin: /home/loucmane/gas-city-ops/.git/worktrees/ga-e0t1.20
Tracked tree is clean. Only the two exact ignored local rule files were installed.

WORKTREE evidence: /var/tmp/ga-e0t1.20-worktree-20260927-r1
result.json SHA-256: 9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af
Local native rules: 0a2c32485d71ef31875010ea810deffb0f2936e8c89bb5da2f7f2aeed5044123
Local deny-only rules: ea2645785163d3f9b6d5ddfe8a08c5ff40b97a8cb1739bca94dd4b2844f15773
Unchanged user defaults: 3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516

PREP evidence: /var/tmp/ga-e0t1.20-prep-20260927-r1
result.json SHA-256: c68c43bf4c5103b1ed9df95ab88a0f33dd7f30fc6cfe8f686635788ea5506f7f
City before: bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1
City prepared: c228dc1e889e794bb1e09da30712789e5acc1f0032b7a76b277009e9c987a0f7
Receipt before: 7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba
Receipt prepared: 58f82e4b3de25a64f0c85aaa008531011d1da6219ab25e6525eeca87a501620a
Revision prepared: 9b6e94d8ecba8baa9b550fbb19a62891c0cf8edb033520adbbe964c0eff3999f
All three typed profiles stayed byte-identical. Only permission_revision and
receipt_sha256 changed in the uninstalled receipt. PREP proved live inputs
unchanged and exact native effective configuration with one target slot.

## Preserved failures and correction evidence

The original ebd7b7da package submission refused before enqueue because its
directory contained a dot, outside the runner's package-name grammar. Signed
0eb66f88 added byte-identical wrappers at admissible entry paths; four tests
exercise that integration boundary.

The admitted WORKTREE r2 then refused during its first pinned policy read.
Access time changed because of that read; digest, ownership, mode, mtime and
ctime stayed unchanged. No intent root, branch, worktree or rules were created.
The successor preserves the old source and adds O_NOATIME to exactly two reads.
The original failure reproduces in a disposable test; all 26 scoped tests pass.
The complete host pre-mutation path passed through the diagnostic with its
first write intercepted. Invoke that diagnostic only with python3 -I -B.
All six workflow verification checks passed before signing.

Review source evidence is preserved in
/tmp/ga-e0t1.20-s1-review-exports and the runner's reviews directory under each
exact candidate commit. Final pair native identities:
01a0e4a6-de3a-73d2-9934-22c9c11a4761 and
01a0e4a6-fd1d-7a91-9987-cebcf5038f82.
Request digests respectively:
3ef747a640e2b124af6a532dc98926023c08a738e7f93ba6a19dfe47fc66d000 and
7927e016027439f1ce7b5516337077f528f51497d9377bbfbcd47f1e667157ff.
No must-fix remained. Optional transaction-level installer/receipt branch tests
remain noted in the earlier S1 review; they are not additional launch authority.

## Next deliverable — S2 operational worker window

Reuse the reviewed gct-e8ex S5 operational machinery, bound to the successful
S1 outputs and the current P13/M12 platform. Do not create another workspace,
redo PREP, edit product code from the coordinator, or dispatch before review.
Prepare the exact BIND/observation/staging/route/resume/watch/contain/restore/
terminal package and test the full no-mutation preconditions before admission.
Two consolidated independent Astra reviews precede execution.

The existing task has exactly one parent-child dependency to ga-e0t1, not a
blocking edge. Its JSON show currently includes the parent's historical notes
and is about 140 KiB. The old Template package's no-edge and 9000-byte assumptions
must not be copied blindly or fixed by deleting the relationship. Bind this
known relationship explicitly and keep full raw evidence; deliver only the
bounded task contract to the worker. The supported plain-text Bead view was
verified read-only: 2162 bytes, full task description and acceptance, parent
identity only without historical parent notes. No new helper is required for
that bounded worker read. This is a package input fact, not permission to modify the
Bead graph, relax ownership, or introduce new product work.

P13 accepted image: /var/tmp/gct-oak5-p13-adoption-20260927/after.json
SHA ab3da79af311190c682d5f1e1146a5c73dd9a66014ca33951d4d38f8ce2331b6
P13 witness: typed-support.json SHA c284a9f4811d569f165c100ebcbaafd38eccf30093fc68eb4e2cd2f7d0adffdb
Provider pins: after.json.provider-pins SHA 82a4a70c43fa1e0d581f6d8c72b8c46c0478bdebca761f7b18cf05d43708765b
M12 manifest SHA 114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9
M12 inspector: /var/tmp/gct-oak5-platform-inspector-m12-20260927/platform-inspect
SHA 0da1ff146cb3e1e1ba7329d669f2135bbc7d26c6c0f35999e6dad1bef88d08c6
Its build-result SHA 2ec7df2d33d0fddc9b9204c51cf65879a683f628dfd2cf2109c04c030416aed0

Carry forward S5 containment double-listing and early-WATCH atime fixes. Preserve
all process/namespace/cache checks. Actual worker startup must prove subscription
auth, exact model and task workspace, policy/sandbox negatives, no unintended MCP
children, exact claim/session, and only the expected worker. The worker edits
only C1 DESIGN.md, slots/slots.py, slots/test_slots.py and produces scoped test
evidence. Candidate review precedes intake; suspend and prove zero residue.

Do not claim this unsigned source-candidate bootstrap is a typed implementation
receipt, managed signing acceptance or Claude/Codex handover. After its source
repair is accepted, resume the original C1/H1/X/H2/C2/intake/retire/M13 sequence.
The later exact C1 cache disposition still requires its specified operator
approval. Step 5 remains terminal evidence and cold-start/recovery documentation.

## Final persistence and non-interference readback

At 23:05:07 CEST the runner queue, active jobs and unfinished list were empty,
HALTED was absent, and suspension-state SHA-256 remained
a3306567b3cf77e6371a870e6df239194574fab8f2dc3090ea55a5eeb14b4817.
Core PID 2800348, signer PID 2310 and broker PID 2940285 retained their original
start epochs with zero restarts. At 23:04:41 CEST all six workflow verification
checks passed. The primary Bead readback contains both successful job outcomes
and preserved refusal dispositions. No relevant child was closed.
