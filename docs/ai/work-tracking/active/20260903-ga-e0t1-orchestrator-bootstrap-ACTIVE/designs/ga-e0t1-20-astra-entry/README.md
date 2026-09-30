# S1 admission-path correction

The first submission at signed candidate ebd7b7da4b37294d4c8c4b32b39c9a45598fe8cc
refused during submit_job.py admission, before enqueue or wrapper execution.
The runner's existing closed package-name grammar excludes dots. The source
package ga-e0t1.20-astra-bootstrap therefore cannot itself be an entry-point path.
The runner remains unchanged. No job ran, no output root was consumed, and no
workspace or rig state changed.

This directory contains byte-identical copies of the two reviewed S1 wrappers
under an admissible hyphen-only directory. They still execute the same exact
digest-pinned source in ga-e0t1.20-astra-bootstrap. The original package and
both SOURCE_PASS reviews remain preserved. No source, frozen input, signature,
receipt, sandbox, policy, lifecycle or output-root checks are changed.

Two fresh request-bound reviews of this signed successor must name these
entry-point paths before submission. The existing reviewed worktree and PREP
executors are unchanged. The original job id never reached the queue; the
successor uses a distinct id and does not erase the refused attempt.

The focused regression directly exercises the installed source's admission
path grammar and proves wrapper byte identity. It covers the exact integration
mistake the initial package tests missed. Broader transaction tests recommended
by the S1 reviewers remain nonblocking follow-ups, not claims of live acceptance.

After two passes: WORKTREE, inspect and record its outcome, then PREP. These
remain preparation-only jobs. S2 lifecycle review and actual worker startup
proof are still required before any product source edit.
