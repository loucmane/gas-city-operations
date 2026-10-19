from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aegis_foundation.obsidian_reconciler import ReconcileError, export_beads

GC_ARGV = (
    "/srv/bin/gc",
    "--city",
    "/srv/city",
    "--rig",
    "hpfetcher",
    "bd",
    "list",
    "--all",
    "--limit",
    "0",
    "--json",
)
SCOPE = b'gc bd: answering from the rig "hpfetcher" store\n'
RECORDS = b'[{"id":"hpf-123","title":"Fixture","status":"open"}]\n'
GATES = (Path("/srv/hpfetcher/.beads.gate.lock"), Path("/srv/city/.beads/dolt.gate.lock"))


def gate_warning(path: Path, reason: str = "read-only file system") -> bytes:
    return (
        "warning: workspace gate acquisition failed, continuing ungated: "
        f"workspacegate: open gate {path}: open {path}: {reason}\n"
    ).encode()


@pytest.mark.parametrize("gate", GATES)
@pytest.mark.parametrize("warning_first", [False, True])
def test_gc_export_accepts_exact_scoped_readonly_warning(monkeypatch, gate, warning_first):
    warning = gate_warning(gate)
    stderr = warning + SCOPE if warning_first else SCOPE + warning
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, RECORDS, stderr),
    )
    assert export_beads(GC_ARGV, 17, gate_paths=GATES) == RECORDS


@pytest.mark.parametrize(
    "stderr,returncode,stdout",
    [
        (SCOPE + gate_warning(Path("/home/loucmane/.beads.gate.lock")), 0, RECORDS),
        (SCOPE + gate_warning(Path("/srv/blog/.beads.gate.lock")), 0, RECORDS),
        (SCOPE + gate_warning(Path("/srv/hpfetcher/../blog/.beads.gate.lock")), 0, RECORDS),
        (SCOPE + gate_warning(GATES[0], "permission denied"), 0, RECORDS),
        (SCOPE + gate_warning(GATES[0]) + b"warning: incomplete results\n", 0, RECORDS),
        (SCOPE + gate_warning(GATES[0]) * 2, 0, RECORDS),
        (SCOPE + gate_warning(GATES[0]) + b"\n", 0, RECORDS),
        (gate_warning(GATES[0]), 0, RECORDS),
        (SCOPE + gate_warning(GATES[0]), 1, RECORDS),
        (SCOPE + gate_warning(GATES[0]), 0, b"not JSON"),
        (SCOPE + gate_warning(GATES[0]), 0, b'{"error":"refused"}'),
        (SCOPE + gate_warning(GATES[0]), 0, b"[1]"),
        (SCOPE + gate_warning(GATES[0]), 0, b"[{}]"),
        (
            SCOPE + gate_warning(GATES[0]).replace(b": open /srv/hpfetcher", b": open /srv/blog"),
            0,
            RECORDS,
        ),
    ],
)
def test_gc_gate_exception_is_fail_closed(monkeypatch, stderr, returncode, stdout):
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, returncode, stdout, stderr),
    )
    with pytest.raises(ReconcileError):
        export_beads(GC_ARGV, 17, gate_paths=GATES)


def test_gc_warning_requires_explicit_gate_binding(monkeypatch):
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, RECORDS, SCOPE + gate_warning(GATES[0])
        ),
    )
    with pytest.raises(ReconcileError, match="stderr"):
        export_beads(GC_ARGV, 17)


@pytest.mark.parametrize("stderr", [SCOPE, SCOPE.rstrip(b"\n")])
def test_gc_export_accepts_only_the_requested_rig_notice(monkeypatch, stderr) -> None:
    def run(argv, **kwargs):
        assert argv == GC_ARGV
        assert kwargs == {"capture_output": True, "timeout": 17, "check": False}
        return subprocess.CompletedProcess(argv, 0, RECORDS, stderr)

    monkeypatch.setattr("aegis_foundation.obsidian_reconciler.subprocess.run", run)
    assert export_beads(GC_ARGV, 17) == RECORDS


@pytest.mark.parametrize(
    "stderr",
    [
        b"",
        b"gc bd: answering from the city store\n",
        b'gc bd: answering from the rig "blog" store\n',
        SCOPE + b"warning: incomplete results\n",
        SCOPE + SCOPE,
        SCOPE + b"\n",
        b"warning: workspace gate acquisition failed, continuing ungated\n",
    ],
)
def test_gc_export_refuses_missing_wrong_or_additional_diagnostics(monkeypatch, stderr) -> None:
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, RECORDS, stderr),
    )
    with pytest.raises(ReconcileError, match="stderr"):
        export_beads(GC_ARGV, 17)


def test_legacy_export_does_not_accept_gc_notice_or_other_warnings(monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, RECORDS, SCOPE),
    )
    with pytest.raises(ReconcileError, match="stderr"):
        export_beads(("/srv/bin/bd", "--readonly", "list", "--json"), 17)


def test_nonzero_export_preserves_stdout_error_beside_gate_warning(monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv,
            1,
            b'{"code":"proxy.readonly.unsupported","error":"strict readonly is unavailable"}',
            b"warning: workspace gate acquisition failed, continuing ungated",
        ),
    )
    with pytest.raises(ReconcileError) as caught:
        export_beads(GC_ARGV, 17)
    assert "refused (1)" in str(caught.value)
    assert "continuing ungated" in str(caught.value)
    assert "proxy.readonly.unsupported" in str(caught.value)


@pytest.mark.parametrize(
    "argv",
    [
        ("/srv/bin/gc", "bd", "list", "--json"),
        GC_ARGV[:3] + GC_ARGV[5:],
        GC_ARGV[:4] + ("other\nrig",) + GC_ARGV[5:],
        GC_ARGV[:2] + ("relative-city",) + GC_ARGV[3:],
        GC_ARGV[:6] + ("close", "hpf-123"),
        GC_ARGV + ("--rig", "other"),
    ],
)
def test_gc_export_requires_one_explicit_complete_rig_read(monkeypatch, argv) -> None:
    def unexpected(*args, **kwargs):
        pytest.fail("invalid gc source must be refused before execution")

    monkeypatch.setattr("aegis_foundation.obsidian_reconciler.subprocess.run", unexpected)
    with pytest.raises(ReconcileError, match="explicit city and rig"):
        export_beads(argv, 17)


def test_scope_notice_never_overrides_nonzero_exit(monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis_foundation.obsidian_reconciler.subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, RECORDS, SCOPE),
    )
    with pytest.raises(ReconcileError, match=r"refused \(1\)"):
        export_beads(GC_ARGV, 17)
