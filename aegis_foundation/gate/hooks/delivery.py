"""The `delivery` native-approval class for the canonical seat (ga-fsfg R3).

A canonical-seat Claude session may push a signed Operations branch, open its pull
request and merge it, one closed command per call. PreToolUse evaluates the call
once (the result is cached on the payload object of that invocation), selects the
worktree `<W>` as the target and writes a create-only binding only when it returns
an approval or audits an advisory seat. PostToolUse finds `<W>` through that
binding, rechecks only `<W>`'s identity and records one delivery-class event there.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import Payload
from .delivery_binding import live_binding_for, read_binding, remove_binding, write_binding
from .delivery_checks import (
    DeliveryRefusal,
    Reader,
    clock,
    config_refusals,
    parse_config,
    run_checks,
)
from .delivery_grammar import (
    COMMAND,
    PR_CREATE,
    PUSH,
    DeliveryRequest,
    delivery_shaped,
    parse_delivery,
)
from .delivery_worktree import (
    Checkout,
    checkout_for_branch,
    checkout_for_commit,
    head_branch,
    resolve_branch,
    verify_checkout,
)
from .payloads import bash_command

DEADLINE_SECONDS = 60.0
KNOWN_MODES = frozenset({"default", "manual", "dontAsk", "acceptEdits", "auto"})
ADVISORY_DELIVERY_REASON = "advisory_delivery_no_native_approval"


@dataclass
class Evaluation:
    """One PreToolUse's delivery evaluation, keyed by session id and tool_use_id."""

    seat: Path
    key: tuple[str | None, str | None]
    request: DeliveryRequest
    worktree: Path
    binding: str | None = None


def _profile_for(seat: Path) -> dict[str, Any] | None:
    from .native_permissions import PROFILE, _profile

    if not (seat / PROFILE).exists():
        return None
    profile = _profile(seat)
    if profile is None or COMMAND not in profile["commands"]:
        return None
    return profile


def delivery_request(seat: Path, payload: Payload) -> tuple[dict[str, Any], DeliveryRequest] | None:
    """The parsed call when the delivery parser owns it at an opted-in canonical seat.

    Anything else returns None and keeps its existing treatment. A delivery-shaped
    command there that breaks the closed grammar raises, which refuses it.
    """

    if payload.tool_name != "Bash":
        return None
    command = bash_command(payload)
    if not delivery_shaped(command):
        return None
    profile = _profile_for(seat)
    if profile is None or str(seat) != profile["canonical_root"]:
        return None
    if payload.cwd != str(seat):
        raise DeliveryRefusal("delivery must originate at the canonical seat")
    return profile, parse_delivery(command, profile)


def delivery_operation(root: Path, command: str) -> str | None:
    """The operation of a valid delivery command, for the passive ledger only."""

    if not delivery_shaped(command):
        return None
    profile = _profile_for(root)
    return parse_delivery(command, profile).operation if profile else None


def delivery_target(seat: Path, payload: Payload, *, post_success: bool = False) -> Path | None:
    """Select `<W>` for a delivery call, or None when the call is not one.

    PreToolUse evaluates once per invocation; the second `target_for` call reuses the
    cached result. PostToolUse resolves `<W>` through the call's binding instead.
    """

    cached = payload.delivery_evaluation
    if (
        not post_success
        and isinstance(cached, Evaluation)
        and cached.seat == seat
        and cached.key == (payload.session_id, payload.tool_use_id)
    ):
        return cached.worktree
    parsed = delivery_request(seat, payload)
    if parsed is None:
        return None
    profile, request = parsed
    if post_success:
        return _posttool_target(seat, payload, profile, request)
    worktree = _evaluate(seat, payload, profile, request)
    payload.delivery_evaluation = Evaluation(
        seat, (payload.session_id, payload.tool_use_id), request, worktree
    )
    return worktree


def _locate(seat: Path, worktree_root: Path, request: DeliveryRequest) -> Checkout:
    """Step 1: find `<W>` by file reads only."""

    if request.operation == PUSH:
        checkout = verify_checkout(Path(str(request.worktree)), seat, worktree_root)
        if head_branch(checkout.admin) != request.branch:
            raise DeliveryRefusal("the worktree's current branch is not the pushed branch")
        return checkout
    if request.operation == PR_CREATE:
        return checkout_for_branch(worktree_root, seat, str(request.branch))
    return checkout_for_commit(worktree_root, seat, str(request.sha))


def _evaluate(
    seat: Path, payload: Payload, profile: dict[str, Any], request: DeliveryRequest
) -> Path:
    from .coordination import _journal
    from .decisions import advisory_enabled
    from .native_permissions import canonical_runtime_tree
    from .runtime_state import current_work_is_observation, required_pending_tracking_events

    if payload.hook_started is None:
        raise DeliveryRefusal("delivery requires the PreToolUse hook-entry clock")
    reader = Reader(
        profile["delivery_home"], profile["delivery_path"], payload.hook_started + DEADLINE_SECONDS
    )
    reader.remaining()
    if payload.permission_mode not in KNOWN_MODES:
        raise DeliveryRefusal("delivery requires a known non-plan permission mode")
    if payload.tool_input.get("run_in_background"):
        raise DeliveryRefusal("delivery refuses run_in_background")
    if not payload.session_id or not payload.tool_use_id:
        raise DeliveryRefusal("delivery requires a session id and a tool_use_id")
    checkout = _locate(seat, Path(profile["worktree_root"]), request)
    if advisory_enabled(checkout.root):
        # decisions.py returns before native_permission for an advisory target, so no
        # binding could be written and the call could never be tracked.
        raise DeliveryRefusal("an advisory target refuses delivery")
    for governed in (seat, checkout.root):
        if current_work_is_observation(governed):
            raise DeliveryRefusal("delivery requires non-observation state at seat and target")
        if required_pending_tracking_events(governed):
            raise DeliveryRefusal("delivery requires resolved pending tracking at seat and target")
    if live_binding_for(seat, checkout.root):
        raise DeliveryRefusal("a delivery call for this worktree is still in flight")
    # Step 2: coordinate's target validation (ready journal, verified ownership, branch
    # form) and the canonical runtime tree check, bounded by the deadline.
    _journal(checkout.root, seat, profile, COMMAND, {})
    canonical_runtime_tree(seat, timeout=reader.timeout())
    # Step 3: the configuration check for <W> and the canonical root.
    for root in (checkout.root, seat):
        listing = reader.git(root, "config", "--list", "--show-scope", "--null", hardened=False)
        refused = config_refusals(parse_config(listing), profile)
        if refused:
            raise DeliveryRefusal(f"delivery configuration refuses {', '.join(refused)} in {root}")
    # Step 4: every other delivery read.
    run_checks(reader, seat, checkout, request, profile)
    reader.remaining()
    return checkout.root


def _posttool_target(
    seat: Path, payload: Payload, profile: dict[str, Any], request: DeliveryRequest
) -> Path:
    """Re-derive `<W>` from the call itself and require the call's binding to agree.

    Only `<W>`'s identity is rechecked; the delivery preconditions (PR state,
    ancestry, signatures, remote reads) are never rerun after the command.
    """

    from .coordination import _journal

    record = read_binding(seat, payload)
    worktree_root = Path(profile["worktree_root"])
    if request.operation == PUSH:
        worktree = Path(str(request.worktree))
    elif request.operation == PR_CREATE:
        worktree = checkout_for_branch(worktree_root, seat, str(request.branch)).root
    else:
        worktree = Path(record["worktree"])
        checkout = verify_checkout(worktree, seat, worktree_root)
        name = head_branch(checkout.admin)
        if name is None or resolve_branch(checkout.common, name) != request.sha:
            raise DeliveryRefusal("the bound worktree's HEAD is not the merged commit")
    if record["operation"] != request.operation or record["worktree"] != str(worktree):
        raise DeliveryRefusal("the delivery binding does not match this call")
    verify_checkout(worktree, seat, worktree_root)
    _journal(worktree, seat, profile, COMMAND, {})
    return worktree


def delivery_evaluation(payload: Payload, worktree: Path) -> Evaluation | None:
    """The cached evaluation when the approved target came from the delivery class."""

    cached = payload.delivery_evaluation
    if isinstance(cached, Evaluation) and cached.worktree == worktree:
        return cached
    return None


def bind(evaluation: Evaluation, payload: Payload, *, approving: bool) -> None:
    """Write this call's binding; an approval checks the deadline once more right after."""

    evaluation.binding = write_binding(
        evaluation.seat, payload, evaluation.worktree, evaluation.request.operation
    )
    started = payload.hook_started
    if approving and (started is None or clock() - started >= DEADLINE_SECONDS):
        discard(payload)
        raise DeliveryRefusal("delivery evaluation exceeded its deadline")


def discard(payload: Payload) -> None:
    """Remove a binding written by this invocation whose approval was not emitted."""

    cached = payload.delivery_evaluation
    if isinstance(cached, Evaluation) and cached.binding is not None:
        remove_binding(cached.seat, payload)
        cached.binding = None


def record_delivery_event(seat: Path, worktree: Path, payload: Payload) -> int:
    """PostToolUse: record one delivery-class event on `<W>`, then consume the binding."""

    from .evidence import record_pending_tracking_event

    failure = None
    try:
        if record_pending_tracking_event(worktree, payload, kind=COMMAND) is None:
            failure = "the worktree has no in-progress current work, so no event was recorded"
    except Exception as exc:  # noqa: BLE001 - reported below; the binding is still consumed.
        failure = f"{type(exc).__name__}: {exc}"
    try:
        remove_binding(seat, payload, required=True)
    except Exception as exc:  # noqa: BLE001 - an unconsumed binding is reported, not hidden.
        failure = failure or f"the binding could not be consumed: {exc}"
    if failure:
        print(
            f"Aegis: delivery tracking on {worktree} is incomplete ({failure}); "
            "stop and reconcile the remote state before further work.",
            file=sys.stderr,
        )
        return 2
    return 0


def delivery_failure() -> int:
    """PostToolUseFailure: remove the failed call's own binding and record nothing."""

    from .decisions import project_root
    from .payloads import load_payload

    payload = load_payload()
    if payload is None or payload.tool_name != "Bash" or not delivery_shaped(bash_command(payload)):
        return 0
    try:
        remove_binding(project_root(), payload)
    except Exception as exc:  # noqa: BLE001 - surfaced to the session; it expires anyway.
        print(
            f"Aegis: the failed delivery call's binding could not be removed ({exc}); "
            "it expires after 30 minutes.",
            file=sys.stderr,
        )
        return 2
    return 0
