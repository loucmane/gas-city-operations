"""Read-only pre-route check for one Operations candidate Bead (gct-lagl HANDOFF 2.10).

  preroute.py <root> <common> <name> <bead-json> <uid> <process-record-json> <process-record-sha256>
              <base-commit> <description-sha256>
  preroute.py record <uid> <controller-pid> <city> <out-json>

Run by the coordinator after the previous candidate session drained and immediately before routing.
The arguments:
- <bead-json> is the coordinator's own `bd show <id> --json` output file.
- <process-record-json> is the city process record the activation `host` step wrote (or a later
  `record` refresh), bound by its digest. It names the controller (pid, exe, start time, cgroup), the
  members of the controller's cgroup, each bound to a reviewed role by exe, argv and start time, the city
  tmux socket and the reviewed hidden-by-design pids. A restarted controller, dolt server or gpg-agent
  makes it stale, which is a stop until it is refreshed. Core keeps the city tmux server alive after its
  last session (exit-empty off), so a refresh needs that server stopped first; the refresh then accepts
  only the reviewed roles, one controller and at most one dolt watchdog and one dolt server, each
  unsandboxed (Seccomp 0, NoNewPrivs 0), in the controller's namespaces, with the watchdog started like
  the controller and dolt as the watchdog's child, so a leftover cannot be laundered into the record.
- <base-commit> is the commit the coordinator created the worktree at.
- <description-sha256> is the digest of the description the coordinator wrote for the Bead.

Security control (deterministic). cgroup.procs lists every member whatever /proc shows. Candidate
processes live either in their pane's tmux-spawn-*.scope (systemd-enabled tmux moves every pane there)
or, if that move failed or raced, in the tmux server's cgroup, the controller's. So a clean city means:
- the controller is the recorded process, still in its recorded cgroup;
- if a city tmux server is running (its pid from SO_PEERCRED on the city socket), it is /usr/bin/tmux
  and, by cgroup membership, in the controller's cgroup;
- the controller's cgroup holds exactly the recorded role-bound members plus that server;
- no cgroup whose path has a tmux-spawn-*.scope component has a member.
Any one clean read proves it for that instant, because membership cannot be hidden; transient controller
children are tolerated only by rereading.

Precondition: a documented assumption about Claude Code's sandbox, not proven or observed by this
package or the candidate window. The operator decided this on 2026-09-24, after declining both
in-sandbox probing and additional monitoring tooling. The checks that do run are this module's city
control and intake review of every changed byte. A seccomp filter and namespaces are inherited by
every descendant, so the assumption, where it holds, binds leftovers too. Sandboxed candidate
commands, and anything they start, are assumed unable to:
- create or connect AF_UNIX sockets: this keeps them off the city tmux socket (timers, hooks, run-shell
  jobs and #() formats are not processes and would later run unsandboxed), the controller's sockets,
  the user and system buses (systemd-run), the WSL interop socket (cmd.exe, powershell.exe) and any
  agent socket, and it stops a leftover from listening on the city socket path;
- reach the host network, including localhost (sshd, the controller API);
- create user namespaces, or write outside the worktree (cgroupfs and /tmp/tmux-<uid> included);
- run an interop binary under /mnt/c;
- ptrace, process_vm_writev or write /proc/<pid>/mem of any process outside the sandbox (the host fact
  Yama ptrace_scope >= 1, checked by the record and by every check, already confines ptrace to
  descendants; the tmux server, controller and dolt are never a pane's descendants);
- change tmux server state through pane output.
The city tmux server is assumed to run in the controller's cgroup, and the operator never starts it
from a shell. Panes whose move failed live in the server's cgroup; this module checks a running server's
cgroup at every call, and the assumption covers the time between calls.
A sandboxed process keeps its seccomp filter and no_new_privs for life, across exec, so a role holder
must show Seccomp 0 and NoNewPrivs 0: a leftover that execs gc or dolt with the reviewed argv still
cannot take a role.
The lane's commands excluded from the sandbox (bd close/show/update, gc hook --claim, gc runtime
drain-ack) are assumed unable to run candidate-controlled code; Core sets BEADS_DIR to the rig, which
keeps a planted ./.beads inert. Where the assumption fails, the control above does not hold, and
intake review is the remaining check.

Consistency checks (not security controls). The hold scan (cwd, root, exe, threads, cmdline, fds, maps,
mounts) and the hidden-set comparison catch accidental holders such as an editor left open. A malicious
process could release its holds for the scan and reopen by path later, so timing evasions of these
checks are accepted; the security control above is what stops a leftover candidate process.

Also refused: a candidate root holding anything but the routed worktree, a worktree that is not a
verified linked worktree at <base-commit>, a gitlink in its tree, a content driver, a status that is not
empty (ignored files included), a Bead whose gc.work_dir is not the worktree, and a description whose
digest differs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import struct
import sys
import time
import tomllib

from candidate_git import Refusal, git, no_drivers, no_gitlinks, require, verify_linked

BEAD = re.compile(r"ga-[a-z0-9]+(\.[0-9]+)?")
CGROUP_FS = Path("/sys/fs/cgroup")
PROC = Path("/proc")
TMUX_TMP = Path("/tmp")
TMUX_SPAWN = "tmux-spawn-"
GC_BIN = "/home/loucmane/gascity/bin/gc"
TMUX_BIN = "/usr/bin/tmux"
DOLT_BIN = "/home/loucmane/gascity/bin/dolt"
CITY_READS = 5
RECORD_KEYS = {"controller", "controller_members", "tmux_socket", "hidden", "ptrace_scope"}
YAMA = Path("/proc/sys/kernel/yama/ptrace_scope")
NS_KINDS = ("mnt", "net", "pid", "user", "cgroup", "ipc", "uts", "time")
ALLOWED_HIDDEN_CGROUPS = frozenset({
    "user@{uid}.service/init.scope",
    "user@{uid}.service/app.slice/gpg-agent.service",
})


def own_lineage(proc: Path = Path("/proc")) -> set[int]:
    lineage, pid = set(), os.getpid()
    while pid > 1 and pid not in lineage:
        lineage.add(pid)
        try:
            pid = int((proc / str(pid) / "stat").read_text().rsplit(") ", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            break
    return lineage


def process_uids(entry: Path) -> set[int] | None:
    try:
        for line in (entry / "status").read_text().splitlines():
            if line.startswith("Uid:"):
                return {int(v) for v in line.split()[1:5]}
    except (OSError, ValueError):
        return None
    return None


def process_holds(root: Path, uid: int, proc: Path = Path("/proc"), pids: set[int] | None = None,
                  members: frozenset[int] = frozenset(), allowed_hidden: frozenset[int] = frozenset()) -> list[str]:
    """Holds on the root by the given pids (default: every pid /proc lists). A consistency check.

    A cgroup member (from `members`) whose entry, status, stat, cwd/root/exe link, task list or per-task
    link is missing during its examination is reported, unless it is one of the exact recorded hidden
    pids. An fd that closes between listing and readlink is not, because fds close routinely. A member
    that really exited mid-scan is also reported; that fails closed and the survey is simply rerun. This
    scan is not the security control (see the module docstring).
    """
    prefix = str(root)
    held = []
    skip = own_lineage(proc)

    def under(value: str) -> bool:
        return value == prefix or value.startswith(prefix + "/")

    def vanished(pid: int, where: str) -> None:
        if pid in members and pid not in allowed_hidden:
            held.append(f"{pid}:hidden-during-scan:{where}")

    if pids is None:
        pids = {int(e.name) for e in proc.iterdir() if e.name.isdigit()}
    for pid in sorted(pids):
        entry = proc / str(pid)
        if pid in skip:
            continue
        if not entry.exists():
            vanished(pid, "entry")
            continue
        uids = process_uids(entry)
        if uids is None:
            if entry.exists():
                held.append(f"{entry.name}:status-unreadable")
            else:
                vanished(pid, "status")
            continue
        if uid not in uids:
            continue
        try:
            state = (entry / "stat").read_text().rsplit(") ", 1)[1].split()[0]
        except (OSError, IndexError):
            if entry.exists():
                held.append(f"{entry.name}:stat-unreadable")
            else:
                vanished(pid, "stat")
            continue
        if state in {"Z", "X"}:
            continue
        hits = []
        for link in ("cwd", "root", "exe"):
            try:
                if under(os.readlink(entry / link)):
                    hits.append(link)
            except FileNotFoundError:
                vanished(pid, link)
                continue
            except OSError:
                hits.append(link + "-unreadable")
        # A thread created without CLONE_FS has its own cwd and root, visible only under task/.
        try:
            for task in (entry / "task").iterdir():
                for link in ("cwd", "root"):
                    try:
                        if under(os.readlink(task / link)):
                            hits.append("task-" + link)
                    except FileNotFoundError:
                        vanished(pid, "task-" + link)
                        continue
                    except OSError:
                        hits.append("task-" + link + "-unreadable")
        except FileNotFoundError:
            vanished(pid, "task")
        except OSError:
            hits.append("task-unreadable")
        try:
            if prefix in (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace"):
                hits.append("cmdline")
        except OSError:
            hits.append("cmdline-unreadable")
        try:
            for fd in (entry / "fd").iterdir():
                try:
                    if under(os.readlink(fd)):
                        hits.append("fd")
                        break
                except FileNotFoundError:
                    continue
        except OSError:
            hits.append("fd-unreadable")
        for name in ("maps", "mountinfo"):
            try:
                if prefix in (entry / name).read_text(errors="replace"):
                    hits.append(name)
            except OSError:
                hits.append(name + "-unreadable")
        try:
            ended = (entry / "stat").read_text().rsplit(") ", 1)[1].split()[0] in {"Z", "X"}
        except (OSError, IndexError):
            ended = None
        if ended is None:
            vanished(pid, "end")
        elif ended:
            vanished(pid, "exited")  # an exiting process's fd table reads as unreadable; members still count
        elif hits:
            held.append(f"{entry.name}:{','.join(sorted(set(hits)))}")
    return held


def user_slice(uid: int) -> Path:
    return CGROUP_FS / f"user.slice/user-{uid}.slice"


def process_facts(pid: int) -> dict:
    """Name, exe, start time, parent, sandbox state (Seccomp, NoNewPrivs), cgroup and argv of one pid."""
    entry = PROC / str(pid)
    comm = (entry / "comm").read_text().strip()
    exe = os.readlink(entry / "exe")
    fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
    status = dict(line.split(":", 1) for line in (entry / "status").read_text().splitlines() if ":" in line)
    lines = (entry / "cgroup").read_text().splitlines()
    require(len(lines) == 1 and lines[0].startswith("0::/"), f"pid {pid} is not on the unified cgroup hierarchy")
    argv = (entry / "cmdline").read_bytes().decode("utf-8", "replace").split("\0")[:-1]
    ns = {kind: os.readlink(entry / "ns" / kind) for kind in NS_KINDS}
    return dict(comm=comm, exe=exe, start=int(fields[19]), ppid=int(fields[1]), seccomp=int(status["Seccomp"]),
                nnp=int(status["NoNewPrivs"]), cgroup=lines[0][3:], argv=argv, ns=ns)


def ptrace_scope() -> int:
    """Yama's ptrace scope: 1 or more confines ptrace and process_vm_writev to descendants."""
    return int(YAMA.read_text().strip())


# r10 (ga-e0t1.18): the managed dolt watchdog survives Core binary replacements. Since broker sequences 14 and 15
# it maps the replaced image 69d00186, which the kernel reports as "<gc> (deleted)"; M7 records the same image as
# WATCHDOG_IMAGE. Only this exact image is admitted for a deleted watchdog executable, and only for that role.
SURVIVING_WATCHDOG_IMAGES = frozenset({"69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9"})


def member_role(facts: dict, city: Path, image=None) -> str | None:
    """The reviewed role of a controller-cgroup member, by kernel exe and the arguments after argv[0].

    `image` is a zero-argument callable returning the sha256 of the member's mapped executable; it is called
    only for a watchdog whose executable is deleted, and that watchdog is admitted only for a surviving image.
    """
    config = f"{city}/.gc/runtime/packs/dolt/dolt-config.yaml"
    roles = {
        "controller": (GC_BIN, ["supervisor", "run"]),
        "dolt-watchdog": (GC_BIN, ["__gc-managed-dolt-scope-watchdog", config, f"{city}/.gc/runtime/packs/dolt/dolt.log",
                                   str(city)]),
        "dolt": (DOLT_BIN, ["sql-server", "--config", config]),
    }
    for role, (exe, args) in roles.items():
        if facts["argv"][1:] != args or facts["seccomp"] != 0 or facts["nnp"] != 0:
            continue
        if facts["exe"] == exe:
            return role
        if (role == "dolt-watchdog" and facts["exe"] == exe + " (deleted)" and image is not None
                and image() in SURVIVING_WATCHDOG_IMAGES):
            return role
    return None


def is_pane(where: str) -> bool:
    return any(part.startswith(TMUX_SPAWN) for part in PurePosixPath(where).parts)


def process_environ(pid: int) -> dict:
    """The environment a process started with (same uid, dumpable)."""
    raw = (PROC / str(pid) / "environ").read_bytes()
    return dict(item.split("=", 1) for item in raw.decode("utf-8", "replace").split("\0") if "=" in item)


def slice_relative(group: str, slice_root: Path) -> str:
    """A cgroup path relative to the user slice; refuses anything outside it or with dot components."""
    parts = PurePosixPath(group).parts
    require(bool(parts) and parts[0] == "/" and all(part not in {"", ".", ".."} for part in parts[1:]),
            f"unsafe cgroup path {group!r}")
    path = CGROUP_FS / group.lstrip("/")
    require(slice_root in path.parents, f"cgroup {group} is outside the user slice")
    return str(path.relative_to(slice_root))


def peer_pid(socket_path: Path) -> int | None:
    """The pid of the tmux server listening on the city socket, or None when no server is running."""
    try:
        info = os.lstat(socket_path)
    except FileNotFoundError:
        return None
    require(stat.S_ISSOCK(info.st_mode), f"{socket_path} is not a socket")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(2)
    try:
        try:
            client.connect(str(socket_path))
        except ConnectionRefusedError:
            return None  # a stale socket file: nothing listens on it
        size = struct.calcsize("3i")
        pid, _uid, _gid = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, size))
    except OSError as exc:
        raise Refusal(f"city tmux socket unreadable: {exc}") from exc
    finally:
        client.close()
    require(pid > 1, f"invalid tmux server pid {pid}")
    return pid


def city_tmux_socket(city: Path, uid: int, controller: int) -> Path:
    """The city tmux socket, derived as Core does, with every override refused.

    Core names the socket after the city (workspace.name, else the directory name) unless [session]
    socket is set, under $TMUX_TMPDIR or /tmp. Overrides in packs or fragments are not composed here; a
    server on another path would still hold its panes in tmux-spawn scopes, which the check watches.
    """
    config = tomllib.loads((city / "city.toml").read_text())
    session = config.get("session") or {}
    require("socket" not in session, "city.toml overrides the tmux socket")
    require(session.get("provider", "") in ("", "tmux"), "city.toml selects a non-tmux session backend")
    environ = process_environ(controller)
    require(not {"TMUX_TMPDIR", "GC_AGENT_SLICE", "GC_SESSION"} & set(environ),
            "controller environment moves the tmux socket or panes, or selects another session backend")
    name = (config.get("workspace") or {}).get("name") or city.name
    require(re.fullmatch(r"[A-Za-z0-9._-]+", name) is not None, f"city name {name!r}")
    return TMUX_TMP / f"tmux-{uid}" / name


def observe_city(slice_root: Path, controller: int, city: Path) -> dict:
    """Record a drained city: the controller, its role-bound cgroup members, the tmux socket, hidden pids."""
    require(isinstance(controller, int) and controller > 1, f"invalid controller pid {controller!r}")
    facts = process_facts(controller)
    require(facts["comm"] == "gc" and member_role(facts, city) == "controller",
            f"controller pid {controller} is not the reviewed gc supervisor")
    scope = ptrace_scope()
    require(scope >= 1, f"Yama ptrace_scope is {scope}; a pane could ptrace the tmux server or controller")
    tmux_socket = city_tmux_socket(city, os.getuid(), controller)
    group = slice_relative(facts["cgroup"], slice_root)
    require(peer_pid(tmux_socket) is None, "a city tmux server is running; record only a drained city")
    members = cgroup_members(slice_root)
    panes = sorted(pid for pid, where in members.items() if is_pane(where))
    require(not panes, f"tmux pane scopes have members: {panes}")
    recorded = []
    for pid in sorted(pid for pid, where in members.items() if where == group):
        member = process_facts(pid)
        # The pid may have been reused between the cgroup.procs read and the /proc reads.
        require(slice_relative(member["cgroup"], slice_root) == group, f"member {pid} left the controller cgroup")
        role = member_role(member, city,
                           image=lambda pid=pid: hashlib.sha256((PROC / str(pid) / "exe").read_bytes()).hexdigest())
        require(role is not None, f"controller cgroup member {pid} has no reviewed role: {member['exe']} {member['argv']}")
        recorded.append(dict(pid=pid, role=role, exe=member["exe"], start=member["start"], ppid=member["ppid"],
                             ns=member["ns"]))
    roles = [m["role"] for m in recorded]
    require(roles.count("controller") == 1 and [m["pid"] for m in recorded if m["role"] == "controller"] == [controller]
            and roles.count("dolt-watchdog") <= 1 and roles.count("dolt") <= 1,
            f"controller cgroup roles are not one controller and at most one watchdog and one dolt: {roles}")
    # Lineage and context: every member shares the controller's namespaces (a bwrap descendant does not);
    # the watchdog is started like the controller, by the user manager; dolt is the watchdog's child.
    watchdogs = [m["pid"] for m in recorded if m["role"] == "dolt-watchdog"]
    for member in recorded:
        require(member["ns"] == facts["ns"], f"member {member['pid']} does not share the controller's namespaces")
        if member["role"] == "dolt-watchdog":
            require(member["ppid"] == facts["ppid"], f"watchdog {member['pid']} is not started like the controller")
        if member["role"] == "dolt":
            require(watchdogs == [member["ppid"]], f"dolt {member['pid']} is not the child of the recorded watchdog")
    hidden = hidden_by_cgroup(slice_root)
    allowed = {group.format(uid=os.getuid()) for group in ALLOWED_HIDDEN_CGROUPS}
    require(set(hidden) <= allowed, f"processes hidden from /proc outside the reviewed cgroups: {hidden}")
    return dict(controller=dict(pid=controller, exe=facts["exe"], start=facts["start"], cgroup=group),
                controller_members=[{k: v for k, v in m.items() if k not in ("ppid", "ns")} for m in recorded],
                tmux_socket=str(tmux_socket), hidden=hidden, ptrace_scope=scope)


def identity_problems(slice_root: Path, record: dict) -> list[str]:
    """The controller and every recorded member are still the recorded processes."""
    recorded = record["controller"]
    try:
        facts = process_facts(recorded["pid"])
        same = (facts["comm"], facts["exe"], facts["start"], facts["seccomp"], facts["nnp"]) == (
            "gc", recorded["exe"], recorded["start"], 0, 0)
        same = same and slice_relative(facts["cgroup"], slice_root) == recorded["cgroup"]
    except (OSError, IndexError, ValueError, KeyError, Refusal):
        same = False
    if not same:
        return ["controller is not the recorded process; refresh the record"]
    problems = []
    for member in record["controller_members"]:
        try:
            now = process_facts(member["pid"])
            same = (now["exe"], now["start"], now["ns"], now["seccomp"], now["nnp"]) == (
                member["exe"], member["start"], facts["ns"], 0, 0)
        except (OSError, IndexError, ValueError, KeyError, Refusal):
            same = False
        if not same:
            problems.append(f"controller cgroup member {member['pid']} ({member['role']}) is not the recorded process")
    return problems


def city_problems(slice_root: Path, record: dict) -> list[str]:
    """The security control: every process a candidate session could have left is accounted for."""
    recorded = record["controller"]
    problems = identity_problems(slice_root, record)
    if problems[:1] == ["controller is not the recorded process; refresh the record"]:
        return problems
    try:
        if ptrace_scope() < 1:
            problems.append("Yama ptrace_scope dropped below 1")
    except (OSError, ValueError) as exc:
        problems.append(f"Yama ptrace_scope unreadable: {exc}")
    recorded_pids = {member["pid"] for member in record["controller_members"]}
    for attempt in range(CITY_READS):
        # The server is re-derived on every read, so a pid it left behind cannot be reused unnoticed.
        members = cgroup_members(slice_root)
        allowed, server_problem = set(recorded_pids), None
        server = peer_pid(Path(record["tmux_socket"]))
        if server is not None:
            where = members.get(server, "outside the user slice")
            try:
                now = process_facts(server)
                exe = now["exe"] if (now["seccomp"], now["nnp"]) == (0, 0) else f"{now['exe']} (sandboxed)"
            except (OSError, IndexError, ValueError, KeyError, Refusal) as exc:
                exe = f"unobservable ({exc})"
            if where != recorded["cgroup"] or exe != TMUX_BIN:
                server_problem = f"city tmux server {server} is not tmux in the controller cgroup: {exe} in {where}"
            allowed.add(server)
        panes = sorted(pid for pid, where in members.items() if is_pane(where))
        inside = {pid for pid, where in members.items() if where == recorded["cgroup"]}
        extra = sorted(inside - allowed)
        missing = sorted(recorded_pids - inside)
        if server_problem:
            return problems + [server_problem]
        if not panes and not extra and not missing:
            # Re-prove every identity after the clean read, so a pid reused during the rereads is caught.
            late = [p for p in identity_problems(slice_root, record) if p not in problems]
            return problems + late
        if attempt + 1 < CITY_READS:
            time.sleep(0.2)
    return problems + [f"city: pane-members={panes} extra-controller-members={extra} missing-recorded={missing}"]


def hidden_by_cgroup(slice_root: Path, proc: Path = Path("/proc")) -> dict[str, list[int]]:
    """Every pid in the slice's cgroup tree that /proc does not show, grouped by cgroup; walk errors refuse."""
    require(slice_root.is_dir(), f"user cgroup slice missing: {slice_root}")
    found: dict[str, list[int]] = {}

    def fail(error):
        raise Refusal(f"cgroup walk error: {error}")

    for directory, _dirs, names in os.walk(slice_root, onerror=fail):
        if "cgroup.procs" not in names:
            continue
        relative = str(Path(directory).relative_to(slice_root))
        try:
            pids = [int(x) for x in (Path(directory) / "cgroup.procs").read_text().split()]
        except (OSError, ValueError) as exc:
            raise Refusal(f"unreadable cgroup.procs in {relative}: {exc}") from exc
        for pid in pids:
            if not (proc / str(pid)).exists():
                found.setdefault(relative, []).append(pid)
    return {group: sorted(pids) for group, pids in found.items()}


def cgroup_members(slice_root: Path) -> dict[int, str]:
    """Every pid in the slice's cgroup tree, with its cgroup; walk and read errors refuse."""
    require(slice_root.is_dir(), f"user cgroup slice missing: {slice_root}")
    members: dict[int, str] = {}

    def fail(error):
        raise Refusal(f"cgroup walk error: {error}")

    for directory, _dirs, names in os.walk(slice_root, onerror=fail):
        if "cgroup.procs" not in names:
            continue
        relative = str(Path(directory).relative_to(slice_root))
        try:
            for pid in (Path(directory) / "cgroup.procs").read_text().split():
                members[int(pid)] = relative
        except (OSError, ValueError) as exc:
            raise Refusal(f"unreadable cgroup.procs in {relative}: {exc}") from exc
    return members


def survey(root: Path, uid: int, slice_root: Path, expected: dict[str, list[int]],
           proc: Path = Path("/proc")) -> list[str]:
    """Holds and hidden processes over every visible pid and every slice member. A consistency check.

    A pid listed in the slice but absent from /proc is hidden (hidepid=2 hides a non-dumpable process),
    never "exited". Only the exact recorded pid sets in the reviewed cgroups are accepted, and a stale
    record is itself a stop. Two passes, both clean. Timing evasions are accepted here; city_problems is
    the security control.
    """
    allowed = {group.format(uid=uid) for group in ALLOWED_HIDDEN_CGROUPS}
    require(set(expected) <= allowed, f"expected-hidden names a non-reviewed cgroup: {sorted(set(expected) - allowed)}")
    recorded = frozenset(pid for pids in expected.values() for pid in pids)
    problems = []
    for _ in range(2):
        members = cgroup_members(slice_root)
        visible = {int(e.name) for e in proc.iterdir() if e.name.isdigit()}
        held = process_holds(root, uid, proc, pids=visible | set(members),
                             members=frozenset(members), allowed_hidden=recorded)
        if held:
            # Busy hosts produce momentary unreadable entries (a process mid-exec or mid-exit); a finding
            # stands only if the same pid is flagged again right away.
            flagged = {int(h.split(":", 1)[0]) for h in held}
            again = {int(h.split(":", 1)[0]) for h in process_holds(root, uid, proc, pids=flagged,
                                                                      members=frozenset(members), allowed_hidden=recorded)}
            held = [h for h in held if int(h.split(":", 1)[0]) in again]
        problems += held
        hidden: dict[str, list[int]] = {}
        for pid, group in cgroup_members(slice_root).items():
            if not (proc / str(pid)).exists():
                hidden.setdefault(group, []).append(pid)
        for group in sorted(set(hidden) | set(expected)):
            if group in allowed and sorted(hidden.get(group, [])) == sorted(expected.get(group, [])):
                continue
            problems.append(f"hidden:{group}:{sorted(hidden.get(group, []))}")
    return sorted(set(problems))


def hidden_processes(slice_root: Path, expected: dict[str, list[int]], uid: int,
                     proc: Path = Path("/proc")) -> list[str]:
    """The hidden-process part of the survey, without a root to hold."""
    return [p for p in survey(Path("/nonexistent-root"), uid, slice_root, expected, proc) if p.startswith("hidden:")]


def check(root: Path, common: Path, name: str, bead_json: Path, uid: int, record: dict, base: str,
          description_sha256: str, slice_root: Path | None = None) -> dict:
    slice_root = slice_root or user_slice(uid)
    city = city_problems(slice_root, record)
    require(not city, f"the city is not quiet: {city}")
    entries = sorted(os.listdir(root))
    require(entries == [name], f"candidate root must hold exactly {name!r}, found {entries}")
    worktree = root / name
    admin = verify_linked(root, common, worktree, name)
    no_drivers(admin, worktree)
    head = git(admin, worktree, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    require(head == base, f"worktree HEAD {head} is not the coordinator's base {base}")
    no_gitlinks(admin, worktree, head)
    status = git(admin, worktree, "status", "--porcelain", "--ignored", "-z", "--untracked-files=all")
    require(status == b"", "routed worktree is not freshly clean")
    problems = survey(root, uid, slice_root, record["hidden"])
    require(not problems, f"processes hold the candidate root or are hidden beyond the recorded ones: {problems}")
    beads = json.loads(bead_json.read_text())
    bead = beads[0] if isinstance(beads, list) else beads
    require(bool(BEAD.fullmatch(str(bead.get("id", "")))), "invalid bead id")
    work_dir = (bead.get("metadata") or {}).get("gc.work_dir")
    require(work_dir == str(worktree), f"gc.work_dir {work_dir!r} is not {worktree}")
    description = hashlib.sha256(str(bead.get("description", "")).encode()).hexdigest()
    require(description == description_sha256, "the Bead description is not the one the coordinator wrote")
    return dict(ok=True, worktree=str(worktree), admin=str(admin), bead=bead["id"], base=head,
                controller=record["controller"])


def load_record(path: Path, digest: str) -> dict:
    """The city process record, bound to its reviewed digest."""
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == digest, "process record is not the reviewed record")
    record = json.loads(raw)
    require(isinstance(record, dict) and set(record) == RECORD_KEYS, "process record shape")
    return record


def encode_record(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=True) + "\n").encode()


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 5 and argv[0] == "record":
            uid = int(argv[1])
            require(uid == os.getuid(), "record runs as the city user")
            raw = encode_record(observe_city(user_slice(uid), int(argv[2]), Path(argv[3])))
            out = Path(argv[4])
            with open(out, "xb") as handle:  # never overwrites
                handle.write(raw)
            result = dict(ok=True, record=str(out), sha256=hashlib.sha256(raw).hexdigest())
        else:
            require(len(argv) == 9, "usage: see module docstring")
            result = check(Path(argv[0]), Path(argv[1]), argv[2], Path(argv[3]), int(argv[4]),
                           load_record(Path(argv[5]), argv[6]), argv[7], argv[8])
    except (Refusal, OSError, ValueError, KeyError) as exc:
        print(json.dumps(dict(ok=False, stop=str(exc))))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
