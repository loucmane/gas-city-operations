# ga-e0t1.20 — S1 preparation, not a worker release

These two jobs reuse the reviewed gct-e8ex S5 mechanisms to prepare an Operations
Astra candidate workspace. They do not execute the C1 source repair, install a
window configuration or receipt, resume a rig, route a Bead, or launch a model.
The standing grant covers preparation; two independent request-bound Astra
reviews must pass before either wrapper is queued through the existing runner.

## Exact task and outputs

The source base is signed Operations c6b789bbe6ff677dd04336803dbf2c2e017812ba.
The new worktree is the direct child
`/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20`, on
`codex/ga-e0t1.20-c1-close-admission`. Only the Gas City worker may later change
C1 `DESIGN.md`, `slots/slots.py` and `slots/test_slots.py`. Its Bead is
ga-e0t1.20 in the gascity store, currently open, unassigned and unrouted.

WORKTREE verifies the source signature, absence of the new path/ref/admin, and
the no-driver/no-attributes/no-gitlink checkout contract before mutation. It
creates exactly this linked worktree through the existing Git operation and
verifies it with the pinned candidate_git implementation. It runs the existing
Template gct-codex-rules installer with explicit unsigned-candidate selection in
a namespace with the host read-only except the newly created rules directory
and the job-owned temporary directory. It adds the separately reviewed deny-only
restriction file. The user rule file and Template assets remain unchanged.
Only those two exact ignored files may exist after installation. No global
trust, signing grants, common-Git write grant, or source edits are installed.
Any partial failure preserves the intent, worktree, branch and failed evidence;
there is no deletion, reset, automatic rollback or replay.

PREP reuses S5's owned normalize/finalize phases and whole-receipt delta proof,
rebound to the current P13 three-profile receipt. It observes the exact native
configuration in read-only, network-isolated namespaces. Every typed Claude
profile must remain byte-identical; only permission revision and receipt digest
may differ. No Claude executable or inference is launched. All output is under
the one fresh preparation root; live city and receipt bytes remain unchanged.

R2 configuration evidence is preserved. R3 adds only two provider restrictions:
the resume command has the same one-task write root as a fresh launch, and the
two MCP servers declared in the source checkout are disabled for fresh and
resumed invocations. This prevents inheriting a broader parent resume command
or launching unrelated MCP tooling. There are still exactly four closed option
choices, one worker slot, and all other shared-provider consumers are held.

## Review and execution order

1. Focused offline and native-confined checks of this consolidated S1 package.
2. Signed clean package, two one-shot independent Astra reviews naming both
   `operator/WORKTREE.sh` and `operator/PREP.sh`, then file every verdict.
3. WORKTREE once; read its actual result and record it. PREP once; read its
   actual result and record it. A runner exit code alone is not a PASS.
4. Bind the resulting exact workspace/rule inventory and image in the S2
   lifecycle package, with containment, restoration, startup and intake checks.
   That package requires its own two reviews. This S1 deliberately has no
   BIND/STAGE/ROUTE/RESUME wrapper and cannot authorize a worker by itself.
5. Before source release, prove the actual worker's claim/session, effective
   policy and trust, subscription authentication, sandbox negatives, absence of
   unexpected children, and exact argv. The literal execpolicy queries are not
   substitutes for those checks. Preserve S5 containment double-listing and
   early-WATCH atime corrections. Do not run coordinator Git in worker roots.

The C1 handover window and its later exact one-field cache disposition remain
separate. These jobs neither close ga-e0t1.20 nor establish signing/provider
parity. The original goal remains active. No HPFetcher or Blog work is touched.

## Assembly and tests

`build.py` is create-only assembly from digest-pinned S5 wrappers and the preserved
inert R2 evidence. It never invokes a wrapper. `assembly.json` binds all outputs.
`inputs.json` losslessly preserves the exact frozen input bytes as base64 with
decoded digest checks. No frozen newline is changed and no whitespace check is
disabled. The original raw inputs also remain in their preserved report directory.
`test_package.py` tests configuration isolation, malformed input refusals, exact
source/rules scope, and wrapper bindings without creating a real worktree or
calling a live mutation. Native checks use the installed Core in a read-only
namespace; the result is still preparation evidence, never worker acceptance.
