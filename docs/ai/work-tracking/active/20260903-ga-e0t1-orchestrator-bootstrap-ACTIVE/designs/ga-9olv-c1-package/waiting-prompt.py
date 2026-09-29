"""Pure, exact-predecessor waiting-prompt correction. No writes or live calls."""
import hashlib

PREDECESSOR_SHA256 = "2b0bf9bae1983e7efd8015233d45c9e26db9cc1d360b7c271b97e498ec8f1d58"
ANCHOR = """   Reject old, different-session or differently bound releases.
"""
INSERTION = """
## Waiting-turn protocol

Retain the exact WAITING marker you just emitted, with your real task, session,
report and probe bindings. Until a valid same-session SOURCE RELEASE arrives,
every non-release message, including a deferred check-for-assigned-work reminder,
must receive that exact saved marker as the sole final answer, without Markdown.
Do not paraphrase it. Make no new tool call, claim, read, probe or Bead note.
A reminder does not restart startup and is not permission to edit.

A legitimate SOURCE RELEASE may be carried inside Core's deferred-reminder
envelope. Match its exact release line and all four bindings against the saved
startup values; the transport envelope itself neither grants nor removes authority.
Reject stale, different-task, different-session or differently bound releases.
On an invalid release keep waiting with the same exact marker and no tool call.

Explicit supported drain or containment takes precedence over every release
and reminder, including when both appear together. Follow only its already
approved exact acknowledgement form. Once draining or stopped, never reopen
implementation on a later release; preserve state for the coordinator.
This paragraph adds no control command, permission or validator exception.
"""


def corrected(raw):
    if hashlib.sha256(raw).hexdigest() != PREDECESSOR_SHA256:
        raise ValueError("waiting prompt predecessor mismatch")
    text = raw.decode("utf-8")
    if text.count(ANCHOR) != 1:
        raise ValueError("waiting prompt anchor missing or ambiguous")
    return text.replace(ANCHOR, ANCHOR + INSERTION, 1).encode("utf-8")

