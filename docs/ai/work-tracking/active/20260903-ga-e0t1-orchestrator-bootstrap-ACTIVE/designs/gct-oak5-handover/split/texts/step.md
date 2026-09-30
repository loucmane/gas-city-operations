# gct-oak5 handover step {NAME}

Handover step {NAME} of `gct-oak5` (Claude -> Codex -> Claude in one worktree). Lane: {LANE}.

Your complete brief is the description of the closed spec Bead {SPEC}. Read it with
`{SHOW} {SPEC}` and follow it exactly. It is the whole contract for this step.

Result contract: close only {STEP}. The final action is to drain and exit: after the close, run
`/home/loucmane/gascity/bin/gc runtime drain-ack` as your final command and claim nothing further.
Never touch any other Bead.
