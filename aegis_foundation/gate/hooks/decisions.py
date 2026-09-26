"""Aegis hook gate: decisions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contracts import (
    AEGIS_ENFORCEMENT_REL,
    AEGIS_GATE_DECISIONS_REL,
    AEGIS_OVERRIDE_TOKEN_REL,
    OVERRIDE_ELIGIBLE_REASONS,
    Payload,
    RECOVERY_CONTRACT,
    RECOVERY_CONTRACT_DEFAULT,
)
from .loaders import _load_ledger_lib_module


def project_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def enforcement_state(root: Path) -> dict[str, Any]:
    state = _read_json_object(root / AEGIS_ENFORCEMENT_REL)
    mode = str(state.get("mode") or "strict").strip().lower()
    if mode not in {"strict", "advisory"}:
        mode = "strict"
    return {
        "mode": mode,
        "set_at": state.get("set_at"),
        "set_by": state.get("set_by"),
        "reason": state.get("reason"),
        "path": AEGIS_ENFORCEMENT_REL,
        "configured": (root / AEGIS_ENFORCEMENT_REL).is_file(),
    }


def enforcement_mode(root: Path) -> str:
    return str(enforcement_state(root).get("mode") or "strict")


def source_commit(root: Path) -> str | None:
    manifest = _read_json_object(root / ".aegis" / "foundation-manifest.json")
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    commit = runtime.get("source_commit") or manifest.get("source_commit")
    return str(commit) if commit else None


def payload_digest(payload: Payload | None, raw_preview: str | None = None) -> str:
    if payload is None:
        data: dict[str, Any] = {"raw_preview": raw_preview or ""}
    else:
        data = {"tool_name": payload.tool_name, "tool_input": payload.tool_input}
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def append_gate_decision(
    root: Path,
    *,
    hook: str,
    payload: Payload | None,
    verdict: str,
    reason: str,
    readiness_state: str | None = None,
    raw_preview: str | None = None,
) -> None:
    mode = enforcement_mode(root)
    report_path = root / AEGIS_GATE_DECISIONS_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "hook": hook,
        "tool_name": payload.tool_name if payload is not None else "unclassifiable",
        "payload_digest": payload_digest(payload, raw_preview),
        "verdict": verdict,
        "reason": reason,
        "readiness_state": readiness_state,
        "mode": mode,
        "source_commit": source_commit(root),
    }
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    _dual_write_gate_decision(root, record, payload)


def _dual_write_gate_decision(root: Path, record: dict[str, Any], payload: Payload | None) -> None:
    """Capsule PR-1c: mirror the advisory decision into the ledger, best-effort.

    The JSONL above stays the primary surface (aegis enforce status and existing
    tests keep reading it); the ledger twin shares the same payload_digest, which is
    the old-vs-new parity key. Any failure here is swallowed — dual-write must never
    break or delay a gate decision.
    """

    try:
        ledger_lib = _load_ledger_lib_module()
        if ledger_lib is None:
            return
        extra = {
            "hook": record.get("hook"),
            "verdict": record.get("verdict"),
            "reason": record.get("reason"),
            "mode": record.get("mode"),
            "source_commit": record.get("source_commit"),
        }
        if record.get("readiness_state"):
            extra["readiness_state"] = record.get("readiness_state")
        event = {
            "ts": record.get("ts"),
            "session_id": payload.session_id if payload is not None else None,
            "cwd": payload.cwd if payload is not None else None,
            "event_type": "gate_decision",
            "tool_name": record.get("tool_name"),
            "payload_digest": record.get("payload_digest"),
            "extra": {key: value for key, value in extra.items() if value is not None},
        }
        ledger = ledger_lib.open_ledger(cwd=root)
        try:
            ledger.append(event)
        finally:
            ledger.close()
    except Exception:  # noqa: BLE001 - dual-write is strictly best-effort.
        return


def advisory_enabled(root: Path) -> bool:
    return enforcement_mode(root) == "advisory"


def advisory_message(hook: str, reason: str) -> None:
    print(
        f"ADVISORY | {hook} would have blocked, but Aegis enforcement mode is advisory: {reason}",
        file=sys.stderr,
    )


def recovery_contract(reason: str) -> dict[str, str]:
    base = RECOVERY_CONTRACT.get(reason, RECOVERY_CONTRACT_DEFAULT)
    return {**RECOVERY_CONTRACT_DEFAULT, **base}


def recovery_block_suffix(reason: str) -> str:
    contract = recovery_contract(reason)
    lines = [
        "",
        "── Aegis recovery contract ──",
        f"blast-radius tier: {contract['tier']}",
        f"copyable safe repair: {contract['repair']}",
    ]
    if contract.get("alt_repair"):
        lines.append(f"alternative: {contract['alt_repair']}")
    lines.append(f"audit destination: {contract['audit']}")
    lines.append(f"escalation: {contract['escalation']}")
    return "\n".join(lines)


def _consume_override_token(root: Path, reason: str) -> dict[str, Any] | None:
    """One-shot, TTL-bounded break-glass token (TM #201).

    Honored ONLY for override-eligible (tier-a/b workflow-state) reasons, and consumed
    on use so it can never become a standing bypass. Returns the token record when a
    valid token is consumed, else None.
    """

    if reason not in OVERRIDE_ELIGIBLE_REASONS:
        return None
    path = root / AEGIS_OVERRIDE_TOKEN_REL
    token = _read_json_object(path)
    if not token:
        return None
    token_reason = str(token.get("reason_class") or "")
    if token_reason not in {"", "any", reason} and token_reason != reason:
        return None
    expires_at_raw = str(token.get("expires_at") or "").strip()
    try:
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        return None
    if expires_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    try:
        path.unlink()  # single use
    except OSError:
        return None
    return token


def gate_block_or_record(
    root: Path,
    payload: Payload,
    message: str,
    *,
    reason: str,
    readiness_state: str | None = None,
) -> int:
    token = _consume_override_token(root, reason)
    if token is not None:
        append_gate_decision(
            root,
            hook="pretooluse",
            payload=payload,
            verdict="allow",
            reason=f"break_glass_override:{reason}",
            readiness_state=readiness_state,
        )
        _record_override_use(root, payload, reason=reason, token=token)
        print(
            f"BREAK-GLASS: one-shot override consumed for {reason} "
            f"(reason: {token.get('note') or 'unspecified'}). Recorded to the ledger.",
            file=sys.stderr,
        )
        return 0
    if advisory_enabled(root):
        append_gate_decision(
            root,
            hook="pretooluse",
            payload=payload,
            verdict="would_block",
            reason=reason,
            readiness_state=readiness_state,
        )
        advisory_message("pretooluse", reason)
        return 0
    try:
        append_gate_decision(
            root,
            hook="pretooluse",
            payload=payload,
            verdict="block",
            reason=reason,
            # The payload is digest-only. Do not copy free-form readiness output
            # (which may quote user content) into the durable denial record.
        )
    except Exception:  # noqa: BLE001 - failed audit must never turn denial into allow.
        pass
    return block(message + "\n" + recovery_block_suffix(reason))


def gate_hard_block(
    root: Path,
    payload: Payload,
    message: str,
    *,
    reason: str,
) -> int:
    """Record and deny a tier-c action regardless of ordinary enforcement mode.

    Advisory mode is intended to relax workflow ceremony, not destructive-operation
    safety. Recording is best-effort so an unavailable ledger can never turn this
    denial into an allow through the degraded-advisory fallback.
    """

    try:
        append_gate_decision(
            root,
            hook="pretooluse",
            payload=payload,
            verdict="block",
            reason=reason,
        )
    except Exception:  # noqa: BLE001 - audit failure must not weaken a hard denial.
        pass
    return block(message + "\n" + recovery_block_suffix(reason))


def _record_override_use(
    root: Path, payload: Payload, *, reason: str, token: dict[str, Any]
) -> None:
    ledger_lib = _load_ledger_lib_module()
    if ledger_lib is None:
        return
    try:
        ledger = ledger_lib.open_ledger(cwd=root)
        try:
            ledger.append(
                {
                    "event_type": "override",
                    "tool_name": payload.tool_name,
                    "payload_digest": payload_digest(payload),
                    "extra": {
                        "reason_class": reason,
                        "note": token.get("note"),
                        "minted_at": token.get("minted_at"),
                        "minted_by": token.get("minted_by"),
                    },
                }
            )
        finally:
            ledger.close()
    except Exception:  # noqa: BLE001 - audit is best-effort, never blocks recovery.
        return


def gate_allow_or_record(root: Path, payload: Payload, *, reason: str) -> int:
    if advisory_enabled(root):
        append_gate_decision(
            root,
            hook="pretooluse",
            payload=payload,
            verdict="allow",
            reason=reason,
        )
        return 0  # Advisory success is never a native permission grant.
    # Called only at successful strict-gate exits, after their existing checks.
    # A silent exit(0) means "defer to Claude permissions", not "approve Bash".
    try:
        from .native_permissions import native_permission

        permission = native_permission(root, payload)
        if permission is not None:
            append_gate_decision(
                root,
                hook="pretooluse",
                payload=payload,
                verdict="allow",
                reason=f"native_permission:{permission}",
            )
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "allow",
                            "permissionDecisionReason": f"aegis-orchestrator:{permission}",
                        }
                    }
                )
            )
    except Exception as exc:  # Fail closed before output, including audit failure.
        _discard_delivery_binding(payload)
        return block(
            "BLOCKED: Claude command profile could not establish an audited approval: "
            f"{type(exc).__name__}: {exc}"
        )
    return 0


def _discard_delivery_binding(payload: Payload) -> None:
    """ga-fsfg R3: an approval that is not emitted leaves no binding holding its worktree."""

    try:
        from .delivery import discard

        discard(payload)
    except Exception:  # noqa: BLE001 - the call is refused either way; the binding expires.
        pass


def block(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def block_unclassifiable_payload(reason: str, raw_preview: str | None = None) -> int:
    details = f"Details: {reason}"
    if raw_preview:
        details = f"{details}\nPayload preview: {raw_preview}"
    return block(
        "BLOCKED by .claude/scripts/pretooluse-gate.sh\n\n"
        "Reason: PreToolUse hook payload could not be parsed or classified safely.\n\n"
        f"{details}\n\n"
        "Aegis fails closed for non-empty or incomplete hook payloads so autonomous agents cannot mutate "
        "a project when the gate cannot render a verdict."
    )
