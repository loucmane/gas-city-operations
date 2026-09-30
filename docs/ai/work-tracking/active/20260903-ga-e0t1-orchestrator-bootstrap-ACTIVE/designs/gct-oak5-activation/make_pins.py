"""Derive pins.json for the live Template-lane activation from the live files and the merged Template (read-only).

  python3 -I -B make_pins.py <out pins.json>

The canonical Template checkout must already hold the merge commit's objects (a refspec-free `git fetch`).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activate  # noqa: E402

TEMPLATE = Path("/home/loucmane/gas-city-template")
# The live canonical checkout (ga-e0t1.15 S3) and Template PR 72's merge commit (gct-mbg6), whose tree equals the
# reviewed intake tree plus the reviewed CI timeout commit.
TEMPLATE_BEFORE = "cfd353f30f465cdf67bbd41fab48812fe5b9617e"
TEMPLATE_COMMIT = "3474abfaec255f7ea4266ce8aa35218afcfc89b0"
TEMPLATE_TREE = "55d7a9df30ef012e4ccc17170a5fca8a4d8f87f9"
CITY = Path("/home/loucmane/gascity/city")
CANDIDATE_ROOT = "/home/loucmane/gas-city-template-candidate-worktrees"
PYTHON = {"name": "python", "executable": {
    "path": "/usr/bin/python3.12", "resolved_path": "/usr/bin/python3.12",
    "sha256": "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f",
    "version_args": ["--version"], "version": "Python 3.12.3"}}
GIT = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
       "GIT_NO_REPLACE_OBJECTS": "1"}


def git(*args):
    return subprocess.run(["/usr/bin/git", "--no-optional-locks", "-C", str(TEMPLATE), "-c", "core.hooksPath=/dev/null",
                           *args], capture_output=True, check=True, env=GIT).stdout


def main(out):
    require = activate.require
    require(activate.sha(Path("/usr/bin/python3.12")) == PYTHON["executable"]["sha256"], "python3.12 digest moved")
    require(git("rev-parse", TEMPLATE_COMMIT + "^{tree}").decode().strip() == TEMPLATE_TREE, "merge tree")
    pins = dict(
        city=str(CITY), template=str(TEMPLATE), candidate_root=CANDIDATE_ROOT, gc="/home/loucmane/gascity/bin/gc",
        env={"PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "/home/loucmane",
             "LANG": "C", "GC_HOME": "/home/loucmane/gascity/home", "GIT_OPTIONAL_LOCKS": "0",
             "BD_DISABLE_METRICS": "1"},
        managed_settings="/etc/claude-code/managed-settings.json", managed_mcp="/etc/claude-code/managed-mcp.json",
        claude_json="/home/loucmane/.claude.json", sandbox_writable=["/tmp", "/var/tmp", "/dev/shm"],
        template_status="?? deploy/\n?? gas_city_template.egg-info/\n",
        user_slice="/sys/fs/cgroup/user.slice/user-1000.slice",
        template_changed=sorted(git("diff", "--name-only", "--no-renames", TEMPLATE_BEFORE, TEMPLATE_COMMIT)
                                .decode().split()),
        uid=1000, python_toolchain=PYTHON,
        registry_before=activate.sha(CITY / "managed/rig-permissions.json"),
        city_before=activate.sha(CITY / "city.toml"),
        fragment_before=activate.sha(CITY / "managed/rig-permissions.toml"),
        template_before=TEMPLATE_BEFORE, template_commit=TEMPLATE_COMMIT, template_tree=TEMPLATE_TREE,
        renderer_sha=activate.digest(git("show", f"{TEMPLATE_COMMIT}:bin/gct-managed-rig-permissions")),
    )
    profile = json.loads(git("show", f"{TEMPLATE_COMMIT}:{activate.PROFILE}"))
    record = activate.candidate_record(profile, PYTHON, CANDIDATE_ROOT)
    pins["candidate_path"] = record["environment"]["PATH"]
    pins["inputs"] = {
        activate.REGISTRY_NAME: activate.digest(activate.new_registry((CITY / "managed/rig-permissions.json").read_bytes(),
                                                                      record)),
        activate.CITY_NAME: activate.digest(activate.new_city((CITY / "city.toml").read_bytes(), CANDIDATE_ROOT)),
    }
    pins["executor"] = activate.executor_digests()
    raw = (json.dumps(pins, indent=1, sort_keys=True) + "\n").encode()
    Path(out).write_bytes(raw)
    print(json.dumps(dict(pins_sha256=activate.digest(raw), inputs=pins["inputs"]), indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
