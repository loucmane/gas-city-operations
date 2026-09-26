"""Derive the M10 city.toml (ga-bebv S3) from the installed city.toml, byte for byte.

  python3 -I -B make_city.py [installed city.toml] [output]

Input: the installed city.toml, 4f7e170f (M5's bytes, unchanged since). Output: CITY_NEW, e5b68c40. Three
exact, count-checked changes, nothing else:
1. [providers.claude] is replaced by providers-claude.toml: options_schema_merge "replace" with the four keys
   permission_mode, effort, model and worktree_access, so no builtin choice survives. The option defaults
   gain effort "max" and worktree_access "none", each equal to its schema default.
2. [providers.codex] is replaced by providers-codex.toml: options_schema_merge "replace" with permission_mode,
   model, effort and worklog_access. [providers.codex-evidence] is carried verbatim, after it.
3. patches-work-dir-roots.toml is appended: eight [[patches.agent]] work_dir_roots entries naming the task
   worktree roots of the Template, Core, Operations candidate, Blog and HPFetcher lanes.
[providers.claude-attention], every rig, override, named session and include stay as they are.

Why: the ga-6umo hotfix (Core 207a78e2, sequence 16) keeps only benign metadata options (model and effort)
and refuses a work_dir outside the configured roots. The live providers still merge by_key over the builtin
schemas, which offer an unrestricted permission mode (claude --dangerously-skip-permissions, codex
--dangerously-bypass-approvals-and-sandbox) and the codex danger-full-access sandbox. Replace mode removes them
from every schema derived from claude or codex (the builtin PermissionModes map itself stays in Core). The
offline Core probe (PLAN-M10.md) resolved all 118 agent and provider entries with the 207a78e2 source: no
unsafe choice, and every launch command and default equals today's.
"""
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).parent
CITY_OLD = '4f7e170fc0503841576c0bb26c33ee5d0aab4e796821f3b1cd874ecef733c591'
CITY_NEW = 'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077'


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def block(lines, start, stop):
    """The exact line range [start header, stop header), each header occurring exactly once."""
    require(lines.count(start) == 1 and lines.count(stop) == 1, 'header cardinality: ' + start.strip())
    first, last = lines.index(start), lines.index(stop)
    require(first < last, 'header order: ' + start.strip())
    return first, last


def derive(old):
    require(digest(old) == CITY_OLD, 'installed city.toml is not the reviewed predecessor')
    claude = (HERE/'providers-claude.toml').read_text()
    codex = (HERE/'providers-codex.toml').read_text()
    patches = (HERE/'patches-work-dir-roots.toml').read_text()
    lines = old.decode().splitlines(True)
    # 1. [providers.claude] up to [providers.claude-attention].
    first, last = block(lines, '[providers.claude]\n', '[providers.claude-attention]\n')
    lines[first:last] = claude.splitlines(True)
    # 2. [providers.codex] up to [defaults]; [providers.codex-evidence] is interleaved and carried verbatim.
    first, last = block(lines, '[providers.codex]\n', '[defaults]\n')
    require(lines.count('[providers.codex-evidence]\n') == 1, 'codex-evidence cardinality')
    evidence_first = lines.index('[providers.codex-evidence]\n')
    # It ends at the next codex schema entry, the first line after it that opens a [[providers.codex.* table.
    evidence_last = lines.index('[[providers.codex.options_schema]]\n', evidence_first)
    require(first < evidence_first < evidence_last < last
            and not any(line.startswith('[[providers.codex.') for line in lines[evidence_first:evidence_last]),
            'codex-evidence position')
    evidence = lines[evidence_first:evidence_last]
    require(sum(1 for line in lines[first:last] if line.startswith('[')
                and not line.startswith(('[providers.codex]', '[providers.codex.', '[[providers.codex.',
                                         '[providers.codex-evidence]', '[providers.codex-evidence.',
                                         '[[providers.codex-evidence.'))) == 0, 'unexpected section in codex range')
    lines[first:last] = codex.splitlines(True) + ['\n'] + evidence
    # 3. The work_dir_roots patches, appended after the last line.
    require(lines[-1].endswith('\n'), 'installed city.toml ends without a newline')
    new = (''.join(lines) + patches).encode()
    require(digest(new) == CITY_NEW, 'derived city.toml differs from the reviewed digest')
    return new


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/loucmane/gascity/city/city.toml')
    new = derive(source.read_bytes())
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_bytes(new)
    print(digest(new))


if __name__ == '__main__':
    main()
