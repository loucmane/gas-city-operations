"""Create-only, non-executing S2 assembly from the signed S5 operational package.

Outputs are a DRAFT. They cannot launch: the cache disposition and startup
release are deliberately unresolved. No inherited consumed job is replayed.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

O = Path('/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap')
D = 'docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/designs/'
SOURCE = '1df3d47ee499b85928c6d34f1aec6e33d1ef2c25'
NAME = 'ga-e0t1-20-astra-window'
OLD = D+'gct-e8ex-window'
NEW = D+NAME
HERE = Path(__file__).parent
WORK = '/home/loucmane/gas-city-ops-candidate-worktrees/ga-e0t1.20'
PREP = '/var/tmp/ga-e0t1.20-prep-20260927-r1'
HEX = re.compile(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['/usr/bin/git', '--no-optional-locks', '-C', str(O), *args],
                          check=True, capture_output=True).stdout


def once(text, old, new):
    assert text.count(old) == 1, (old[:120], text.count(old))
    return text.replace(old, new)


def replace_function(text, name, replacement):
    [node] = [n for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    lines = text.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1]) + replacement.rstrip()+'\n' + ''.join(lines[node.end_lineno:])


MAP = {
    '/home/loucmane/gas-city-template-worktrees/gct-mbg6': WORK,
    '/home/loucmane/gas-city-template/.git/worktrees/gct-mbg6': '/home/loucmane/gas-city-ops/.git/worktrees/ga-e0t1.20',
    '/home/loucmane/gas-city-template/.git': '/home/loucmane/gas-city-ops/.git',
    'codex/gct-mbg6-template-candidate-lane': 'codex/ga-e0t1.20-c1-close-admission',
    'cfd353f30f465cdf67bbd41fab48812fe5b9617e': 'c6b789bbe6ff677dd04336803dbf2c2e017812ba',
    'gas-city-template/codex': 'gascity/codex',
    'gas-city-template--codex': 'gascity--codex',
    '/var/tmp/gct-mbg6-worktree-20260926-r1': '/var/tmp/ga-e0t1.20-worktree-20260927-r1',
    '/var/tmp/gct-mbg6-prep-20260926-r1': PREP,
    '/var/tmp/gct-mbg6-terminal-20260926-r1/observed-after.json': '/var/tmp/gct-oak5-p13-adoption-20260927/after.json',
    '959767c4dd0648bf882ac39b1ddb19330bfe8e6f94f69003a97f1908d888684a': 'ab3da79af311190c682d5f1e1146a5c73dd9a66014ca33951d4d38f8ce2331b6',
    '/var/tmp/ga-bebv-p11-adoption-20260927': '/var/tmp/gct-oak5-p13-adoption-20260927',
    'a2016797ca0c91dadaa770b9496dc93c919ebffd4f22290da0309087f0c9c675': 'c284a9f4811d569f165c100ebcbaafd38eccf30093fc68eb4e2cd2f7d0adffdb',
    '/var/tmp/ga-bebv-p11-input-20260927': '/var/tmp/gct-oak5-p13-input-20260927',
    '68fb232e0c940140db9f5a41bf62652eca19115240a18a1b118698f5884611c1': '7b8472f6cc339f261abc32b32e27b1d7f2a3c494ec24be021c396dbac2d9969d',
    '/var/tmp/ga-bebv-platform-inspector-m10-20260927': '/var/tmp/gct-oak5-platform-inspector-m12-20260927',
    'e1bb4fc9ac4884b4ad96710b05006c1148349781e826976d3bfef868752beac8': '0da1ff146cb3e1e1ba7329d669f2135bbc7d26c6c0f35999e6dad1bef88d08c6',
    'ab96575ef37b03e514c3c098a292dac8d7183946f5221b091cfa9cdc97a8bc62': '2ec7df2d33d0fddc9b9204c51cf65879a683f628dfd2cf2109c04c030416aed0',
    '1f87b7b86afc322c385aed0dbc22491b511b6704f07bb5e9078f342aff7d0e3a': '367056c801f85a4409589d231a0e91243f7ed1d9c6ded9a2e658865c8e3b0ad4',
    '2b902a83577acf71f9dd93a97d43d8478f7c4b291b0992e8ba5a5e44fe66f7f2': '114b4a000471ee145d494732db361521ea237b3e4857607b06720b7b105327b9',
    'e5b68c40a422225ae7b246fb0c579363c1167b4e4fac466717b0ee0237073077': 'bdcec2549fae330ed4aedc2c25563f1917e2bfd39e1caea4be443536f94c69b1',
    '1dc5c539982656be664b447d6e9ade344c0975cf0625b185e60df2c2ece69b40': 'c228dc1e889e794bb1e09da30712789e5acc1f0032b7a76b277009e9c987a0f7',
    '06a3f58a060a20b28d0bea86105e22278ef8983f0f80cba4d725788cd3a8bbd5': '7185414ebade17a1fdd7d485564e85f6ad8d7e0230983c21bf917f1ed27fb0ba',
    '7a1e2ed1df4a652fe31fe361d3fcf017e71c32f539d5e2b4a62b1e802ba3f06c': '58f82e4b3de25a64f0c85aaa008531011d1da6219ab25e6525eeca87a501620a',
    '03f16ea2f9d46393f749c93a397f5a6020210d0f2252fe0a45205ee4263ce712': 'a61666b33528c1cb8b497f55d9c6b8b37df2ce74ed9853345de8d7321e18f58f',
    '480c2dd891073a3a798b2747961e68a94d5717a950ef1e219c11b15acb1efab6': '9b6e94d8ecba8baa9b550fbb19a62891c0cf8edb033520adbbe964c0eff3999f',
    '983e77f482732c4545dc3a7d0e4b425f11e8f2d9c386d0f570670812e53b9a2f': 'c68c43bf4c5103b1ed9df95ab88a0f33dd7f30fc6cfe8f686635788ea5506f7f',
    'c66bab3c40693762c54c998efa8b5f8bab2813391ba15a9318a00b7b33f2ef0c': '136f2b728a6713c123dab4a79a6fb34934e578bf01cf57658603afdb46166955',
    'gct-e8ex-window': NAME,
    'gct-mbg6': 'ga-e0t1.20',
}


def rebind(name, text):
    for old, new in MAP.items():
        text = text.replace(old, new)
    text = re.sub(r'(/var/tmp/ga-e0t1\.20-[a-z%-]+)-20260926-r[123]', r'\1-20260927-r1', text)
    # Explicit rig selectors only. Preserve the complete four-rig inventory set.
    for old, new in (("'--rig','gas-city-template'", "'--rig','gascity'"),
                     ("'--rig', 'gas-city-template'", "'--rig', 'gascity'"),
                     ("['rig','resume','gas-city-template'", "['rig','resume','gascity'"),
                     ("['rig','suspend','gas-city-template'", "['rig','suspend','gascity'"),
                     ("['rig', 'suspend', 'gas-city-template'", "['rig', 'suspend', 'gascity'")):
        text = text.replace(old, new)
    return text


def base(text):
    text = once(text, 'CACHE_PREV_NS = 1790470648629115669', 'CACHE_PREV_NS = 1790510685769555369')
    text = once(text, 'CACHE_PINNED_NS = 1790491430741191162', 'CACHE_PINNED_NS = None  # Exact new disposition still requires review and authority.')
    text = replace_function(text, 'approved_candidate_cache_image', '''def approved_candidate_cache_image(prior):
    require(CACHE_PINNED_NS is not None, 'S2 cache disposition is not approved or pinned')
    value=json.loads(json.dumps(prior))
    entry=value['cache']['inventory'][CACHE_DIRECTORY]
    for key in ('mtime_ns','ctime_ns'):
        require(entry[key] == CACHE_PREV_NS, 'cache disposition preimage')
        entry[key] = CACHE_PINNED_NS
    return value''')
    # Historical exception code cannot become permission for this fresh window.
    for name in ('approved_historical_image', 'approved_epoch_image', 'approved_restore_image',
                 'approved_coordinator_cache_image', 'approved_recovery_image'):
        tree = ast.parse(text)
        [node] = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        args = ast.unparse(node.args)
        text = replace_function(text, name, 'def '+name+'('+args+"):\n    raise RuntimeError('historical disposition is not authority for this window')")
    start = text.index('# s5 disposition (')
    end = text.index('def active_epoch(o):', start)
    text = text[:start]+'''def verified_lifecycle(terminal=False):
    s=module(HERE/'suspension-lineage.py',LINEAGE_SHA)
    b,o,owned=load_support()
    require(not list(ROOT.glob('suspension-*-failure.json'))
        and not list(ROOT.glob('suspension-*-refused-after.json')), 'unreviewed stranded lifecycle')
    return s.chain(record('suspension-baseline.json'),lifecycle_records(s),
        suspension_record(o),str(ROOT),terminal)

'''+text[end:]
    # Contract import is source-bound, no ambient module resolution.
    marker = "def load_support():\n"
    text = once(text, marker, "def contract():\n    return module(HERE/'contract.py', '"+sha((HERE/'contract.py').read_bytes())+"')\n\n\n"+marker)
    text = once(text, "require(result['stdout']=='','worker not clean')", "contract().validate_rule_status(result['stdout'].encode())")
    text = once(text, "['status','--porcelain=v1','--ignored','--untracked-files=all']", "['status','--porcelain=v1','--ignored','--untracked-files=all','-z']")
    text = once(text, 'def suspension_status_matches(value, expected, probe_partial=False):',
                'def suspension_status_matches(value, expected, probe_partial=False, *, census, action):')
    start = text.index("    running=[a for a in value['agents'] if a['running']]")
    end = text.index("    signals=value['health'].get('signals',[])", start)
    text = text[:start]+"    running=contract().running_rows(value,census,action)\n"+text[end:]
    text = once(text, "        status=json.loads(r['stdout'])", """        status=json.loads(r['stdout'])
        census=json.loads(phase(action+'-sessions-'+str(index),GC+['session','list','--json'],
            b,owned,timeout=min(15,max(1,deadline-time.monotonic())))['stdout'])""")
    text = once(text, 'suspension_status_matches(status,expected,probe)',
                'suspension_status_matches(status,expected,probe,census=census,action=action)')
    # Fail closed until live startup proof is integrated into the release path.
    text = once(text, "action=sys.argv[1]\n", "action=sys.argv[1]\n    require(False, 'DRAFT package has no execution admission')\n")
    return text


def bind(text):
    text = once(text, "WORKTREE_SHA='310f75d0d1e29e99a8305a03caa4245e81dd445045986b60eca50bc8bb0108aa'",
                "WORKTREE_SHA='9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af'")
    start = text.index('    made=json.loads(w.read(WORKTREE_RESULT))')
    end = text.index("    assert not os.path.lexists(w.ROOT)", start)
    text = text[:start]+'''    made=json.loads(w.read(WORKTREE_RESULT,
        '9760bb7c2f8de075619e9c8d0b53e03f4b9d40a07aa45dc5c26380ad1cbec4af'))
    assert made['ok'] is True and made['worker_launched'] is False and made['tracked_clean'] is True
    assert made['worktree']==WORK and made['admin']==str(w.ADMIN) and made['base']==w.BASE
    assert made['branch']=='codex/ga-e0t1.20-c1-close-admission'
    assert made['local_rules']==w.contract().RULES and made['default_rules_unchanged'] is True
'''+text[end:]
    start = text.index("    assert before['status']=='open'")
    end = text.index("    metadata={'gc.work_dir':WORK}", start)
    text = text[:start]+"    w.contract().validate_task(before,'unbound')\n"+text[end:]
    text = once(text, "    ROOT.mkdir(mode=0o700);w.ROOT=ROOT", "    raise RuntimeError('DRAFT package has no execution admission')\n    ROOT.mkdir(mode=0o700);w.ROOT=ROOT")
    text = once(text, "    metadata={'gc.work_dir':WORK}", """    metadata={'gc.work_dir':WORK}
    note=w.contract().BOUND_NOTE
    (ROOT/'sandbox-negative').mkdir(mode=0o700)
    w.save('sandbox-negative-fixture.json',dict(path=str(ROOT/'sandbox-negative'),
        purpose='one new sacrificial file must be denied by the actual worker sandbox'))""")
    text = once(text, "    run('task-bind',argv)", "    argv += ['--append-notes',note]\n    run('task-bind',argv)")
    text = once(text, "        executor_sha256=_SOURCE_SHA,worker_launched=False))",
                "        executor_sha256=_SOURCE_SHA,worker_launched=False,note=note))")
    text = once(text, "    assert after['metadata']==metadata", "    assert after['metadata']==metadata\n    assert after['notes']==note\n    w.contract().validate_task(after,'bound')")
    text = once(text, "if key not in ('metadata','updated_at'):", "if key not in ('metadata','notes','updated_at'):")
    return text


def route(text):
    text = once(text, "root=Path('/home/loucmane/gas-city-template-worktrees')", "root=Path('/home/loucmane/gas-city-ops-candidate-worktrees')")
    start = text.index('    # Template variant of no_drivers:')
    end = text.index('    attempts=[]', start)
    text = text[:start]+'''    cg.no_drivers(admin,work)
    w.contract().validate_rule_status(cg.git(admin,work,'status','--porcelain','--ignored','-z','--untracked-files=all'))
    for rel,pin in w.contract().RULES.items():
        w.read(work/rel,pin)
        assert stat.S_IMODE((work/rel).lstat().st_mode)==0o644,'local policy mode'
    w.read(Path('/home/loucmane/.codex/rules/default.rules'),w.contract().DEFAULT_RULES)
'''+text[end:]
    start = text.index('    # gct-e8ex split r8/r9 reviews:')
    end = text.index('    checked=dict(', start)
    text = text[:start]+'''    w.contract().validate_task(shown_bead,'bound')
    # The full JSON is preserved above. The supported bounded text view omits parent history.
    brief=run('preroute-brief',w.GC+['--rig','gascity','bd','show','ga-e0t1.20'])['stdout']
    assert len(brief.encode())<9000 and 'ga-e0t1.20' in brief,'bounded worker brief'
'''+text[end:]
    text = once(text, "    ROOT.mkdir(mode=0o700);w.ROOT=ROOT", "    raise RuntimeError('DRAFT package has no execution admission')\n    ROOT.mkdir(mode=0o700);w.ROOT=ROOT")
    return text


def watch(text):
    old = "        w.directory_preservation(a, z)"
    new = """        # Same prospective clock bound and accounting as final preservation.
        # This changes only comparison copies, never source metadata.
        baseline=json.loads(w.read(before_path))
        policy=w.module(BASE.parent/'cache-atime-policy-r1.py',
            '61c3e38e4475061c658a853036922742ab2ce69d44a4577e3f91490674047783')
        import time
        def sample():
            first=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
            real=time.time_ns()
            last=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
            return dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                real_ns=real,boot_before_ns=first,boot_after_ns=last)
        clock=dict(start=sample(),end=sample())
        bound=policy.bounds(baseline['cache_access_clock'],clock)
        w.account_read_times(dict(directories=a),dict(directories=z),bound)
        w.directory_preservation(a, z)"""
    return once(text, old, new)


def assemble():
    names = git('ls-tree', '-r', '--name-only', SOURCE, OLD).decode().splitlines()
    names = [name for name in names if (name.endswith('.py') and '/generators/' not in name
             and not name.endswith(('test_successor.py','prep-r11.py','worktree-task-r1.py')))
             or ('/operator/' in name and name.endswith('.sh') and not name.endswith(('PREP.sh','WORKTREE.sh')))]
    sources = {name[len(OLD)+1:]: git('show', SOURCE+':'+name) for name in names}
    out = {}
    for name, raw in sources.items():
        text = rebind(name, raw.decode())
        if name == 'window-base-r11.py': text = base(text)
        elif name == 'bind-task-r5.py': text = bind(text)
        elif name == 'route-task-r5.py': text = route(text)
        elif name == 'watch-r11.py': text = watch(text)
        elif name == 'suspension-lineage.py': text = text.replace("'gas-city-template'", "'gascity'")
        elif name == 'audit-queue-r3.py':
            text = text.replace("('template', ['--rig', 'gascity'])", "('gascity', ['--rig', 'gascity'])")
            text = text.replace("store=='template'", "store=='gascity'")
            text = text.replace("r['name'] != 'gas-city-template'", "r['name'] != 'gascity'")
        elif name == 'hold-r11.py': text = text.replace("r['name'] == 'gas-city-template'", "r['name'] == 'gascity'")
        if name.endswith('.sh'):
            # No draft wrapper can run, even if somebody tries to submit it.
            text = once(text, '#!/bin/sh\n', '#!/bin/sh\necho "DRAFT ONLY - not admitted for execution" >&2\nexit 125\n')
        out[name] = text.encode()
    for name in ('contract.py','test_contract.py','task-own-fields.json','worker-startup.py','WORKER-BRIEF.md'):
        out[name] = (HERE/name).read_bytes()
    note=('Operational startup contract for ga-e0t1.20: read '+str(O/NEW/'WORKER-BRIEF.md')+
          ' sha256 '+sha(out['WORKER-BRIEF.md'])+'. Verify and run '+str(O/NEW/'worker-startup.py')+
          ' sha256 '+sha(out['worker-startup.py'])+' inside the actual worker sandbox with its real session ID. '+
          'No product edit until the coordinator verifies startup and releases that exact session. '+
          'No staging signing task close restart or delegation. Return an uncommitted candidate only.')
    out['contract.py'] = once(out['contract.py'].decode(),
        "BOUND_NOTE = 'DRAFT worker brief is not yet bound'", 'BOUND_NOTE = '+repr(note)).encode()
    # Track dependency substitutions until the acyclic source-binding graph settles.
    history = {name: {sha(raw)} for name, raw in sources.items()}
    history.setdefault('contract.py',set()).add(sha((HERE/'contract.py').read_bytes()))
    for _ in range(40):
        for name, raw in out.items(): history.setdefault(name,set()).add(sha(raw))
        mapping = {old:sha(out[name]) for name, old_set in history.items() for old in old_set if old != sha(out[name])}
        # S5 retained an earlier observer's runtime digest only for its consumed recovery.
        mapping['f8a163b00f87b199f6678582832cdeb1c0d7ee93740ca309ea3328c0cfd006ff'] = sha(out['observe-integrity-r11.py'])
        newer = {name: HEX.sub(lambda m:mapping.get(m[0],m[0]),raw.decode()).encode()
                 if name.endswith(('.py','.sh')) else raw for name,raw in out.items()}
        if newer == out: break
        out = newer
    else: raise RuntimeError('source binding graph did not settle')
    for name,raw in out.items():
        if name.endswith('.py'): ast.parse(raw, filename=name)
    return sources,out


def main(output):
    root=Path(output)
    assert not root.exists(), 'create-only output'
    sources,out=assemble()
    root.mkdir(mode=0o700)
    for name,raw in out.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.s2-draft.v1', source_commit=SOURCE,
        source_files={name:sha(raw) for name,raw in sources.items()},
        files={name:sha(raw) for name,raw in out.items()}, execution_admitted=False,
        remaining=['startup release proof and worker brief','post-terminal scoped intake',
                   'final cache disposition and independent reviews'])
    with (root/'assembly.json').open('x') as stream: json.dump(manifest,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__': main(*sys.argv[1:])
