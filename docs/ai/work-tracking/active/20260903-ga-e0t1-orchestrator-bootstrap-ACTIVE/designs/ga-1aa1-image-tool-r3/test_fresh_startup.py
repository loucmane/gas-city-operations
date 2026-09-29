"""Synthetic fresh-startup proofs; no provider, credentials or host mutation."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import stat
import types

import pytest

HERE = Path(__file__).parent


def module(name):
    path = HERE / name
    out = types.ModuleType(name)
    out.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), out.__dict__)
    return out


c = module("contract.py")
v = module("startup-validation.py")


def routed():
    task = copy.deepcopy(c.BASELINE)
    task.update(notes=c.BOUND_NOTE, updated_at="2026-09-29T10:00:00Z")
    task["metadata"] = {"gc.work_dir": c.WORK, "gc.routed_to": c.TARGET}
    return task


def session():
    return dict(id="ci-new", session_name="codex-ci-new", created_at="2026-09-29T10:00:01Z",
                last_active="2026-09-29T10:00:05+00:00", template=c.TARGET,
                rig="gascity", provider=c.PROVIDER, work_dir=c.WORK, closed=False)


def live():
    task = routed()
    task.update(status="in_progress", assignee="codex-ci-new", started_at="2026-09-29T10:00:02Z",
                updated_at="2026-09-29T10:00:04Z")
    task["metadata"].update({"gc.session_id": "ci-new", "gc.session_name": "codex-ci-new",
                             "gc.work_branch": v.CLAIM_BRANCH})
    task["notes"] += "\nSTARTUP READY: ga-1aa1 report_sha256=" + "a" * 64
    return task


def test_real_claim_store_branch_is_distinct_from_worker_branch():
    assert v.CLAIM_BRANCH == "agent/upstream-pending-create-lease"
    assert v.BRANCH == c.BRANCH and v.CLAIM_BRANCH != v.BRANCH
    assert v.live_task(live(), routed(), session(), c, "a" * 64).startswith("STARTUP READY")
    assert v.monitoring_state(live(), routed(), session(), "2026-09-29T10:00:06Z") == {
        "kind": "exact-fresh-claim", "source_release_authorized_by_this_check": False}


@pytest.mark.parametrize("key,value", [
    ("gc.session_id", "ci-old"), ("gc.session_name", "codex-ci-old"),
    ("gc.work_branch", "wrong"), ("gc.work_branch", c.BRANCH),
    ("gc.work_dir", "/wrong"), ("gc.routed_to", "blog/codex"),
    ("gc.failure_reason", "progress_stall"), ("gc.session_affinity", ""),
    ("gc.continuation_group", ""),
])
def test_claim_metadata_is_closed(key, value):
    task = live()
    task["metadata"][key] = value
    with pytest.raises(RuntimeError):
        v.live_task(task, routed(), session(), c, "a" * 64)


@pytest.mark.parametrize("kind", ["duplicate-note", "changed-source", "wrong-owner", "wrong-start",
                                  "prior-start", "wrong-label", "old-status"])
def test_fresh_claim_refusals(kind):
    task, before = live(), routed()
    if kind == "duplicate-note":
        task["notes"] += "\nSTARTUP READY: ga-1aa1 report_sha256=" + "a" * 64
    elif kind == "changed-source":
        task["description"] += " changed"
    elif kind == "wrong-owner":
        task["assignee"] = "codex-ci-other"
    elif kind == "wrong-start":
        task["started_at"] = "2026-09-29T09:00:00Z"
    elif kind == "prior-start":
        before["started_at"] = "2026-09-28T13:01:54Z"
    elif kind == "wrong-label":
        task["labels"] = ["needs/operator"]
    else:
        task["status"] = "closed"
    with pytest.raises(RuntimeError):
        v.live_task(task, before, session(), c, "a" * 64)


def test_omitted_best_effort_branch_is_not_source_identity():
    task = live()
    del task["metadata"]["gc.work_branch"]
    v.live_task(task, routed(), session(), c, "a" * 64)
    argv = [v.CODEX, "--model", "gpt-6-astra", "--ask-for-approval", "never",
            "--sandbox", "workspace-write", "-c", "model_reasoning_effort=high",
            "-c", "sandbox_workspace_write.writable_roots=" + json.dumps([c.WORK], separators=(",", ":")),
            "-c", "mcp_servers.serena.enabled=false", "-c", "mcp_servers.aegis.enabled=false", "Bound prompt"]
    assert v.process_arguments(argv)["flags"]["--model"] == "gpt-6-astra"
    with pytest.raises(RuntimeError):
        v.process_arguments([x.replace(c.WORK, "/wrong") for x in argv])


def waiting_records():
    marker = ("WAITING FOR SOURCE RELEASE: ga-1aa1 session=ci-new report_sha256="
              + "a" * 64 + " probe_sha256=" + "b" * 64)
    return [
        {"type": "session_meta", "payload": {"id": "synthetic-provider"}},
        {"type": "response_item", "timestamp": "2026-09-29T10:00:05.000Z",
         "payload": {"type": "message", "role": "assistant", "phase": "final_answer",
                     "content": [{"type": "output_text", "text": marker}]}},
        {"type": "event_msg", "timestamp": "2026-09-29T10:00:05.100Z",
         "payload": {"type": "task_complete", "last_agent_message": marker, "turn_id": "turn-synthetic"}},
    ]


def wire(rows):
    return ("\n".join(json.dumps(x) for x in rows) + "\n").encode()


def test_completed_native_waiting_turn_positive_and_negative():
    rows = waiting_records()
    proof = v.waiting_turn(wire(rows), session(), "a" * 64, "b" * 64, "2026-09-29T10:00:06Z")
    assert proof["completed_waiting_turn"] is True
    assert proof["source_release_authorized_by_this_check"] is False
    for mutated in (rows[:-1], [rows[0], rows[2], rows[1]]):
        with pytest.raises(RuntimeError):
            v.waiting_turn(wire(mutated), session(), "a" * 64, "b" * 64, "2026-09-29T10:00:06Z")
    for old in ("ci-new", "ga-1aa1", "a" * 64, "b" * 64):
        with pytest.raises(RuntimeError):
            v.waiting_turn(wire(rows).replace(old.encode(), b"wrong"), session(),
                           "a" * 64, "b" * 64, "2026-09-29T10:00:06Z")


def test_native_denial_requires_real_request_response_and_posture():
    context = dict(cwd=c.WORK, approval_policy="never", model="gpt-6-astra", effort="high",
                   **copy.deepcopy(v.NATIVE_POSTURE))
    rows = [
        {"type": "session_meta", "payload": {"id": "provider-id", "cwd": c.WORK, "cli_version": "0.153.4"}},
        {"type": "turn_context", "payload": context},
        {"type": "response_item", "payload": {"type": "function_call", "call_id": "deny-1",
         "name": "exec_command", "arguments": json.dumps({"cmd": "gpg --version", "workdir": c.WORK})}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "deny-1",
         "output": "exec command rejected: forbidden by policy"}},
    ]
    assert v.denial_from_rollout(wire(rows), "provider-id")["provider_session_id"] == "provider-id"
    for field, value in (("model", "other"), ("effort", "low"), ("cwd", "/wrong")):
        bad = copy.deepcopy(rows)
        bad[1]["payload"][field] = value
        with pytest.raises(RuntimeError):
            v.denial_from_rollout(wire(bad), "provider-id")
    bad = copy.deepcopy(rows)
    bad[-1]["payload"]["output"] = "Process exited with code 1"
    with pytest.raises(RuntimeError):
        v.denial_from_rollout(wire(bad), "provider-id")
    with pytest.raises(RuntimeError):
        v.denial_from_rollout(wire(rows) + wire(rows[2:]), "provider-id")


def test_new_task_evidence_parent_requires_private_mode():
    directory = dict(mode=0o700, type=stat.S_IFDIR)
    after = {p: dict(directory) for p in (".gc", ".gc/worker-evidence",
                                        ".gc/worker-evidence/" + c.TASK, v.EVIDENCE)}
    raw = b"Owned workspace write proof.\n"
    after[v.EVIDENCE + "/positive-write.txt"] = dict(
        mode=0o600, type=stat.S_IFREG, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    after[v.EVIDENCE + "/startup.json"] = dict(mode=0o600, type=stat.S_IFREG, size=1, sha256="a" * 64)
    v.pristine_startup({}, after, "a" * 64, {})
    after[".gc/worker-evidence/" + c.TASK]["mode"] = 0o755
    with pytest.raises(RuntimeError):
        v.pristine_startup({}, after, "a" * 64, {})


def complete_workspace():
    before = {p: dict(mode=0o644, type=stat.S_IFREG, size=4, sha256="c"*64)
              for p in c.SOURCE_PATHS}
    after = dict(copy.deepcopy(before), **copy.deepcopy(c.RUNTIME_IMAGE))
    for p in ('.gc/worker-evidence', '.gc/worker-evidence/'+c.TASK, v.EVIDENCE):
        after[p] = dict(mode=0o700, type=stat.S_IFDIR)
    raw = b'Owned workspace write proof.\n'
    after[v.EVIDENCE+'/positive-write.txt'] = dict(mode=0o600, type=stat.S_IFREG,
        size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    after[v.EVIDENCE+'/startup.json'] = dict(mode=0o600,type=stat.S_IFREG,size=1,sha256='a'*64)
    return before,after


def test_fresh_startup_through_terminal_workspace_admits_exact_evidence_parent():
    before,after = complete_workspace()
    v.pristine_startup(before,after,'a'*64,c.RUNTIME_IMAGE)
    for path in c.SOURCE_PATHS:
        after[path]['sha256'] = 'd'*64
    v.workspace_delta(before,after,c.RUNTIME_IMAGE,c.SOURCE_PATHS,True)


@pytest.mark.parametrize('path', sorted(c.RUNTIME_IMAGE))
def test_every_missing_runtime_entry_refuses_source_release(path):
    before,after = complete_workspace()
    del after[path]
    with pytest.raises(RuntimeError):
        v.pristine_startup(before,after,'a'*64,c.RUNTIME_IMAGE)


@pytest.mark.parametrize('path', ['.gc/worker-evidence', '.gc/worker-evidence/'+c.TASK, v.EVIDENCE])
@pytest.mark.parametrize('mode,kind', [(0o755,stat.S_IFDIR),(0o700,stat.S_IFREG)])
def test_terminal_evidence_parent_authority_is_exact(path,mode,kind):
    before,after = complete_workspace()
    after[path] = dict(mode=mode,type=kind)
    with pytest.raises(RuntimeError):
        v.workspace_delta(before,after,c.RUNTIME_IMAGE,c.SOURCE_PATHS,True)


def test_unmodified_runtime_checks_match_successful_predecessor():
    old = HERE.parent / "ga-e0t1-20-astra-window/startup-validation.py"
    raw = old.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "1a7751461abeece16453018e0c083cdea7f7ca16341449aef7d07a14af8c342e"
    normalized = raw.decode().replace("ga-e0t1.20", "ga-1aa1").replace(
        "c6b789bbe6ff677dd04336803dbf2c2e017812ba", c.BASE).replace(
        "codex/ga-1aa1-c1-close-admission", c.BRANCH).replace(
        ".gc/worker-evidence/ga-1aa1/r11", v.EVIDENCE)
    before = {n.name: ast.dump(n) for n in ast.parse(normalized).body if isinstance(n, ast.FunctionDef)}
    after = {n.name: ast.dump(n) for n in ast.parse((HERE / "startup-validation.py").read_text()).body
             if isinstance(n, ast.FunctionDef)}
    changed = {"claim_time", "live_task", "monitoring_state", "pristine_startup", "workspace_delta"}
    assert set(after) == set(before) | {"claim_metadata"}
    for name in set(before) - changed:
        assert after[name] == before[name], name
    assert "ci-9dp7z" not in (HERE / "startup-validation.py").read_text()
