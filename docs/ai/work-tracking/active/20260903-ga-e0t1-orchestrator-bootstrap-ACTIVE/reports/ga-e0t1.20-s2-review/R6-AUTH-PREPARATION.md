# R6 supplemental authentication-output preparation

2026-09-28 Europe/Stockholm. ga-e0t1.20 remains incomplete. No worker retry yet.
R5-LIVE-OUTCOME.md records the consumed window and verified exact restoration.

## Narrow defect and correction

The pinned CLI returns exit 0 and the exact ChatGPT identity, plus the exact
local PATH-alias warning under write protection. The old whole-output equality
refuses that result. The diagnostic's combined status-output SHA-256 is
72118305a60fa509ac4bfac8a406509a6022f2584a36f7adf9f7bed08891a71d.

The pure auth_status_r6.py grammar accepts only the original successful identity
or exactly this warning followed by that identity:
WARNING: proceeding, even though we could not create PATH aliases: Read-only file system (os error 30)

It requires integer exit zero, bounded byte outputs and strict UTF-8. Unknown
warnings, duplicate/mixed identities, API identity, malformed status and nonzero
exit still refuse with constant error text. No raw status or credential value
is included in evidence. CLI binary pin and provider-override checks stay intact.

auth_probe_r6.py derives from exact consumed R5 probe
1766846356f763e1b98ed6276b916e53daf7493786e4f73fb7f6648146ab1f67.
An AST equality regression proves every other statement unchanged after removing
only the old two-statement predicate and the replacement call plus pure helper.
No new worker import path or permission grant: the helper is embedded.

The corrected function accepted the actual same pinned CLI's read-only status
reproduction with subscription_only true and path_alias_warning true. This is
a controller-side read-only diagnostic, not a replacement for the owed actual
worker's startup, sandbox, claim, native-denial and source-release proofs.
The missing raw R5 worker status stream remains honestly missing.

## Preparation only

New additive assets: PRECLAIM-R6.md, worker-startup-r6.py, prompt-prep-r6.py,
operator/PROMPT-PREP-R6.sh, prompt-prep-r6-manifest.json.
All R5 assets remain byte-identical to ff1212c23576ff3f2da13ba4ddf703c18ce9bc68.

The new wrapper uses the existing signed-clean-candidate and fresh-root contract,
and the existing native preparation engine. It writes only the new root
/var/tmp/ga-e0t1.20-prompt-prep-20260928-r6 and its log. It installs nothing,
changes no Bead or lifecycle, and launches no worker.
It binds R5 terminal result and the exact ci-rks41 supported-close result
independently. It does not relabel observer worker_launched=false as proof that
R5 never had a worker.
Typed profiles remain exact; the native receipt delta must remain only the
composition revision and self-digest. Only the isolated target prompt changes.
Existing helper source, common-Git exception, signer, service and permissions
are unchanged.

Manifest SHA-256:
90efa0921e492bf4dcff56dd43b048f89f75177cda09f4e4168c9d67d5935d3a.
Exact generated file and authoring hashes are in that manifest.

## Tests

34 focused tests passed in 0.12 seconds:
/tmp/ga-e0t1-20-r6-prep-tests-20260928-r1.xml
SHA-256 bc0b7e5b289f650156d116bf52ecbbf6012c27036c7a658e2baddf694160ff1d.

Full operational generator suite: 610 passed, zero failures/skips, 40.20 seconds:
/tmp/ga-e0t1-20-r6-prep-full-20260928-r1.xml
SHA-256 8ebd5503de2d41480e1a467bf95bf63a14fa7bbdce3347a4c14906929812302a.

Pure assembly fixtures only; the focused tests do not run native preparation.
No product, runtime adapter, hook or installed plugin source changed.

## Required next gates

Sign exact preparation candidate; obtain two fresh independent Astra reviews.
Only after both pass, preserve the verified terminal latch and queue only
PROMPT-PREP-R6 through the existing runner. Do not replay R5.
After successful native preparation, assemble a complete append-forward window
binding the new outputs and preserved R5 session/claim/STOPPED-note disposition,
then test and independently review that complete successor before any worker.
No live acceptance or product delivery is implied by this preparation.
