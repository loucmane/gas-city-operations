# Task-link R1 known partial and bounded R2 completion

2026-09-28, Stockholm CEST. Existing goal and standing completion grant unchanged.

## R1 actual outcome

Both native Astra reviews returned SOURCE_PASS for signed clean
3c7a8c8043b6c06837b9db949af32917afba8244. Request digest
d41e7528dd566656f40df6ee64063e884ca62dd02fe19fa65d65fa5504ffc8c9.
Native reviewer identities 01a0e6e6-38e2-7d42-9cec-b1bc0ae0105a
and 01a0e6e7-0818-7d71-bbf9-64ca4e56eb32 are exported under
/tmp/ga-e0t1-20-link-reviews-20260928-r1 and filed in the jobrunner ledger.

The host job ran 09:30:41 to 09:31:49 CEST. Removal succeeded and
complete intermediate child/parent images matched. The add exited 1 before
its storage call: the CLI's isChildOf check uses the dotted ID and rejects
all dep-add types aimed from this child to its parent. This was missed by
the implementation and both source reviews. Storage-level compatibility and
fake API tests did not prove the real CLI entrypoint. No success is claimed.

Preserved evidence root:
/var/tmp/ga-e0t1.20-link-reconciliation-20260928-r1

Exact files:
- before.json 404cde16554560c6c1dc1c9ba0b85f910e2774fb6f33481e840d2d2f4fb5581b
- removed-after.json 96fe63db6309f8516107844eb35a7e087453632713f6dbdf3d578f841f3c6595
- related-write-phase.json fec65cd6ad5e2fb1eebe7ae46bacd104df3dcd50e28a868251d6a38121c0f844

Fresh supported host reads independently confirmed both complete live Beads
equal removed-after.json. Task stays open, unassigned, with identical own fields,
route and workspace, but zero dependency/dependent counts and no parent field.
The parent retains every prerequisite and its own fields with only dependent
count decremented. Normal ready query returns exactly ga-e0t1.20.
All four rigs and the city remain suspended, zero native sessions/running agents.
The failed command was reaped with no signals or survivors and the job unit is
inactive. No worker launched. Runner remains HALTED. No second remove or add
was attempted; no rollback was guessed. This is known partial, not pre-mutation
for the whole package and not a successful window.

## Mechanism reassessment, not another dep-add retry

The installed CLI advertises the dedicated supported dep relate operation.
Cached Beads v1.2.2 cmd/bd/relate.go documents a bidirectional see-also relationship
without blocking or hierarchy. It calls AddDependency twice with DepRelatesTo,
whose serialized type is relates-to. It does not take dep-add's isChildOf path.
The two calls are not an atomic pair transaction and this limitation is explicit.

R2 completes only the missing informational association through one fixed
gc city-and-rig-scoped dep relate ga-e0t1.20 ga-e0t1 --json command.
It does not repeat removal, route, binding, claim, resume, or any completed job.
The representation is now bidirectional relates-to, not the unsupported
unidirectional related command in R1. It preserves the documented independent
repair intent and all genuine blocks prerequisites; no CLI or ready guard is
disabled. This is the supported informational API, not a forced dependency,
raw SQL or protected-store mutation.

The executor pins R1 source and exact failure/intermediate evidence. Before
writing, it requires both full live images still match, actual stable host,
restored city and receipt, exact suspension bytes, all rigs suspended, zero
sessions, and sole-target normal readiness. Intent is durable before the one
command. Afterwards it verifies both relates-to edges, own fields, counts,
and all original prerequisite records. Only dependency presentation order is
normalized; duplicate/extra records still refuse. Ready and blocked inventories
must remain exact and the final host is rechecked.

Any command error, one-sided association, unexpected delta, timeout, or
containment failure stops without replay or automatic fallback. The consumed
R2 root is preserved. A final result is readiness/association evidence only,
not worker admission. The next worker window still needs fresh signed bindings
and two reviews and must not replay completed BIND or ROUTE.

## Test boundary and review questions

28 focused offline tests pass at
/tmp/ga-e0t1-20-link-completion-focused-r2.xml.
The fake postimage is independently specified, not computed by production
projection. Tests execute the actual transition and distinguish intent-save,
read, write, and post-write-guard failures. They reject one-sided links,
prerequisite/status/owner/notes/count drift, duplicate dependencies, wrong
acknowledgement and a consumed/structural preimage.
No claim of native live API proof follows from these tests.

Independent review must trace the real relate CLI and storage entrypoints,
validate the graph projection including native JSON shapes, evaluate the
known-partial completion against the standing grant, and verify failure
containment and no lifecycle/worker authority. Review must not reuse R1 PASS.
No changes to R1, the worker's three product files, installed CLI, or runtime.
Bead note is deferred until this tightly pinned recovery is disposed, to avoid
changing the parent's exact frozen image during recovery. This report and the
supported workflow log preserve the failure immediately.
