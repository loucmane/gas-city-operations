"""Derive pins.json for the live activation from the live files and the merged Template (read-only).

  python3 -I -B make_pins.py <out pins.json>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activate  # noqa: E402

HERE = Path(__file__).resolve().parent
# r10: ga-e0t1.15 S3 moved the canonical checkout to cfd353f3 (PR 70 e6195b10 plus PR 71), so base and target are
# equal, the reviewed change set is empty and the checkout step only proves the lane files.
TEMPLATE_BEFORE = "cfd353f30f465cdf67bbd41fab48812fe5b9617e"
TEMPLATE_COMMIT = "cfd353f30f465cdf67bbd41fab48812fe5b9617e"
CITY = Path("/home/loucmane/gascity/city")
PYTHON = {"name": "python", "executable": {
    "path": "/usr/bin/python3.12", "resolved_path": "/usr/bin/python3.12",
    "sha256": "e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f",
    "version_args": ["--version"], "version": "Python 3.12.3"}}


def show(commit, path):
    return subprocess.run(["/usr/bin/git", "--no-optional-locks", "-C", "/home/loucmane/gas-city-template", "show",
                           f"{commit}:{path}"], capture_output=True, check=True,
                          env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
                               "GIT_CONFIG_GLOBAL": "/dev/null"}).stdout


profile = json.loads(show(TEMPLATE_COMMIT, "managed/profiles/gascity-operations-candidate-claude.json"))
record = activate.candidate_record(profile, PYTHON)
pins = dict(
    city=str(CITY), template="/home/loucmane/gas-city-template", ops="/home/loucmane/gas-city-ops",
    candidate_root="/home/loucmane/gas-city-ops-candidate-worktrees", gc="/home/loucmane/gascity/bin/gc",
    env={"PATH": "/home/loucmane/gascity/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "/home/loucmane",
         "LANG": "C", "GC_HOME": "/home/loucmane/gascity/home", "GIT_OPTIONAL_LOCKS": "0", "BD_DISABLE_METRICS": "1"},
    managed_settings="/etc/claude-code/managed-settings.json", managed_mcp="/etc/claude-code/managed-mcp.json",
    claude_json="/home/loucmane/.claude.json", sandbox_writable=["/tmp", "/var/tmp", "/dev/shm"],
    template_status="?? deploy/\n?? gas_city_template.egg-info/\n",
    user_slice="/sys/fs/cgroup/user.slice/user-1000.slice",
    template_changed=sorted(subprocess.run(
        ["/usr/bin/git", "--no-optional-locks", "-C", "/home/loucmane/gas-city-template", "diff", "--name-only",
         "--no-renames", TEMPLATE_BEFORE, TEMPLATE_COMMIT], capture_output=True, text=True, check=True,
        env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}).stdout.split()),
    uid=1000, candidate_path=record["environment"]["PATH"], python_toolchain=PYTHON,
    registry_before=activate.sha(CITY / "managed/rig-permissions.json"),
    city_before=activate.sha(CITY / "city.toml"),
    fragment_before=activate.sha(CITY / "managed/rig-permissions.toml"),
    template_before=TEMPLATE_BEFORE, template_commit=TEMPLATE_COMMIT,
    renderer_sha=activate.digest(show(TEMPLATE_COMMIT, "bin/gct-managed-rig-permissions")),
)
pins["prompt_source"] = str(HERE / "operations-candidate-prompt.template.md")
live = activate.Live(pins)
registry = activate.new_registry((CITY / "managed/rig-permissions.json").read_bytes(), record)
city = activate.new_city((CITY / "city.toml").read_bytes(), live.prompt)
pins["inputs"] = {"rig-permissions.json": activate.digest(registry), "city.toml": activate.digest(city),
                  activate.PROMPT_NAME: activate.sha(Path(pins["prompt_source"]))}
pins["executor"] = activate.executor_digests()
Path(sys.argv[1]).write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
print(json.dumps(pins["inputs"], indent=1))
