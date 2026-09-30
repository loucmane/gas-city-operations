"""Create-only, non-executing S2 assembly from the signed S5 operational package.

Default outputs remain inert drafts. --execution-candidate prepares final bytes
for independent review, not admission. No inherited consumed job is replayed.
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
FINAL_CACHE_NS = 1790575978569227372
FINAL_OBSERVATION_SHA = '9bfb716ad6431661de9aed0cd903cfb88104fb0743b834ab81dca057ec77508b'
COMPLETED_BIND_EXECUTOR = '9fd6c49adecf7fb991f9b8cd2c6279c25fcf73455bfa0911609a2079928495e7'


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
    # Preserve failed r1 and successful r2/r3 observations. New package
    # pins receive a new observation root; completed BIND is never replayed.
    text = text.replace('/var/tmp/ga-e0t1.20-integrity-20260927-r1',
                        '/var/tmp/ga-e0t1.20-integrity-20260928-r4')
    # Explicit rig selectors only. Preserve the complete four-rig inventory set.
    for old, new in (("'--rig','gas-city-template'", "'--rig','gascity'"),
                     ("'--rig', 'gas-city-template'", "'--rig', 'gascity'"),
                     ("['rig','resume','gas-city-template'", "['rig','resume','gascity'"),
                     ("['rig','suspend','gas-city-template'", "['rig','suspend','gascity'"),
                     ("['rig', 'suspend', 'gas-city-template'", "['rig', 'suspend', 'gascity'")):
        text = text.replace(old, new)
    return text


def base(text):
    document=ast.parse(text).body[0]
    lines=text.splitlines(keepends=True)
    text='"""ga-e0t1.20 bounded Astra candidate window, rebound from signed S5.\n\nS1 WORKTREE and PREP are completed. The accepted platform is P13; the current\nsource contains no reusable historical lifecycle exception. This package is\nnot C1 or handover acceptance and introduces no Claude invocation.\n"""\n'+''.join(lines[document.end_lineno:])
    start=text.index('# The accepted image is ')
    end=text.index('ACCEPTED = ',start)
    text=text[:start]+'# Accepted P13 observation; all host, pin and protected fields remain exact.\n'+text[end:]
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
    text=text.replace("        # The ga-e0t1.20 TERMINAL record was taken on this epoch after RESTORE; only the coordinator-cache\n        # disposition of this window applies (approved_candidate_cache_image).",
        "        # Compare against P13 with this package's exact cache-directory time pair only.")
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
    text = once(text, "        save('preflight-pass.json',dict(ok=True,executor_sha256=_SOURCE_SHA,worker_launched=False))",
                """        common=module(HERE/'common-snapshot-r1.py','ASSEMBLY_COMMON_SHA')
        common_before=common.observe()
        require(common_before['candidate_branch']==BASE and not common.baseline_problems(common_before),
            'candidate common Git baseline')
        require(not common.compare(common_before,common.observe()),'common Git changed during baseline')
        save('common-before.json',common_before)
        validator=module(HERE/'startup-validation.py','ASSEMBLY_VALIDATOR_SHA')
        # No circular imports: this reader is the existing bounded worker probe.
        probe=module(HERE/'worker-startup.py','ASSEMBLY_PROBE_SHA')
        workspace_before=validator.workspace_image(WORK,probe.read_regular)
        require(workspace_before==validator.workspace_image(WORK,probe.read_regular),'workspace baseline drift')
        save('workspace-before.json',workspace_before)
        client_paths=('/home/loucmane/.codex/config.toml','/home/loucmane/.codex/hooks.json',
            '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy',
            '/home/loucmane/.local/libexec/gas-city-workflow/root-policy-v1/root-policy.json')
        save('client-inputs-before.json',{path:digest(probe.read_regular(Path(path))) for path in client_paths})
        save('preflight-pass.json',dict(ok=True,executor_sha256=_SOURCE_SHA,worker_launched=False))""")
    return text


def bind(text):
    document=ast.parse(text).body[0]
    text='"""Bind only the Operations candidate workspace and exact startup contract.\n\nThe existing nonblocking parent edge is verified, not removed. No receipt,\nclaim, route, runtime configuration or worker implementation is created here.\n"""\n'+''.join(text.splitlines(keepends=True)[document.end_lineno:])
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
    # This is a consumed receipt identity, not a dependency on newly generated
    # executable bytes. The binding from signed 3c993172 must never be replayed.
    text = re.sub(r"^BIND_SHA='[0-9a-f]{64}'$",
        "BIND_SHA='COMPLETED_BIND_EXECUTOR_SHA'",text,flags=re.M)
    start = text.index('    s=BIND.lstat()')
    end = text.index("    w.read(w.CITY/'city.toml'",start)
    block = text[start:end]
    for name,pin in (
        ('binding-intent.json','0f85dbaa6de8c174c3bc4950955777bb23621cb3bc8bd55ce9546c5e029e4b37'),
        ('result.json','0e8003f3fa54558537cd93dcd2863ab5bcd0aef8be8af1ec11c198472ad022d2'),
        ('task-after.json','e58d90d46f6422aeb6d65a135daf41389fb5d1b9e0115f1019f6b2027abf7dcb')):
        block = once(block,"w.read(BIND/'"+name+"')", "w.read(BIND/'"+name+"','"+pin+"')")
    text = text[:start]+"    bound=completed_binding(w)\n"+text[end:]
    helpers = 'def completed_binding(w):\n'+block+'    return bound\n\n\n'+'''def continued_task(current,bound):
    # gc embeds parent audit history in each child read. Retain exact own
    # fields and all parent fields except a monotonic append-only audit update.
    from datetime import datetime
    assert set(current)==set(bound), 'bound task field set'
    for key in bound:
        if key!='dependencies':assert current[key]==bound[key], ('bound task changed',key)
    old=bound['dependencies'];new=current['dependencies']
    assert isinstance(old,list) and isinstance(new,list) and len(old)==len(new)==1
    old=old[0];new=new[0]
    assert set(old)==set(new), 'parent field set'
    for key in old:
        if key not in ('notes','updated_at'):assert new[key]==old[key], ('parent changed',key)
    assert isinstance(new['notes'],str) and new['notes'].startswith(old['notes']), 'parent audit erased'
    a=datetime.fromisoformat(old['updated_at']);z=datetime.fromisoformat(new['updated_at'])
    assert a.tzinfo is not None and z.tzinfo is not None and z>=a, 'parent audit time'


'''
    text = once(text,'def main():\n',helpers+'def main():\n')
    text = once(text,"    assert before==bound and before['status']=='open' and not before.get('assignee')",
        "    continued_task(before,bound)\n    assert before['status']=='open' and not before.get('assignee')")
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
    text = once(text, "        after = json.loads(w.read(stage_event))['after']", """        after = json.loads(w.read(stage_event))['after']
        bound = w.read_time_bounds(json.loads(w.read(WINDOW/'before.json'))['cache_access_clock'])
        w.save('read-route-observation.json',dict(before=after,after=now,window=bound))
        now = w.route_read_account(after,now,bound)""")
    text = once(text, "        z = json.loads(json.dumps(w.directories(o)))", """        z = json.loads(json.dumps(w.directories(o)))
        baseline = json.loads(w.read(before_path))
        bound = w.read_time_bounds(baseline['cache_access_clock'])
        raw = json.loads(json.dumps(dict(before=a,after=z,window=bound)))
        w.save('read-directory-observation.json',raw)
        # Check read eligibility against the real post-reload parent times,
        # before the existing diagnostic-only route normalization below.
        z['city']['.beads'], parent_reads = w.read_time_policy().metadata(
            str(w.CITY/'.beads'),a['city']['.beads'],z['city']['.beads'],bound,renamed=True)""")
    return once(text, "        w.directory_preservation(a, z)", """        reads = w.account_read_times(dict(directories=a),dict(directories=z),bound)
        w.read_time_evidence('directories',raw['before'],raw['after'],parent_reads+reads,bound)
        w.directory_preservation(a, z, read_window=bound)""")


def read_time_base(text):
    text = replace_function(text, 'stable_read_times', '''def stable_read_times(paths=None, now_ns=None):
    # Operator-authorized four-object accounting replaces the 19-hour scheduling
    # assumption. Reads remain relatime-bound; every actual delta is checked and
    # recorded at preservation, route and suspension comparison boundaries.
    now_ns = time.time_ns() if now_ns is None else now_ns
    for path in stable_read_paths() if paths is None else paths:
        flags = os.statvfs(path).f_flag
        require(flags & os.ST_RELATIME and not flags & os.ST_NOATIME,
                'access-time mount policy is not relatime: ' + str(path))
        s = os.lstat(path)
        require(all(type(v) is int and 0 <= v <= now_ns for v in
                    (s.st_atime_ns, s.st_mtime_ns, s.st_ctime_ns)),
                'invalid or future read metadata: ' + str(path))''')
    text = once(text, 'def directory_preservation(before, after):',
                'def directory_preservation(before, after, *, read_window=None):')
    marker = "    for section, target in [('city','city.toml'),('provision','receipt.json')]:"
    text = once(text, marker, '''    if read_window is not None:
        changes = []
        for section, key, path, renamed in (
            ('city', '.', str(CITY), True),
            ('provision', '.', str(RECEIPT.parent), True),
            ('city', '.beads', str(CITY/'.beads'), False)):
            aligned, delta = read_time_policy().metadata(path, a[section][key],
                z[section][key], read_window, renamed=renamed)
            z[section][key] = aligned
            changes.extend(delta)
        read_time_evidence('directories', before, after, changes, read_window)
'''+marker)
    text = once(text, 'def preservation(before, after, city_pin, receipt_pin):',
                'def preservation(before, after, city_pin, receipt_pin, *, read_window=None):')
    text = once(text, "    directory_preservation(a.pop('directories'),z.pop('directories'))",
                "    directory_preservation(a.pop('directories'),z.pop('directories'),read_window=read_window)")
    text = once(text, "        require(a['pins'][SUSPENSION] == record('suspension-baseline.json')['pin'], 'suspension original binding')",
                "        require(suspension_pin_equal(a['pins'][SUSPENSION],record('suspension-baseline.json')['pin']), 'suspension original binding')")
    text = once(text, "        require(z['pins'][SUSPENSION] == endpoint, 'suspension final binding')",
                "        require(suspension_pin_equal(z['pins'][SUSPENSION],endpoint), 'suspension final binding')\n        z['pins'][SUSPENSION] = endpoint")
    text = once(text, "        suspension_record(o),str(ROOT),terminal)",
                "        suspension_record(o),str(ROOT),terminal,read_account=suspension_read_equal)")
    text = once(text, "previous,before,str(ROOT))", "previous,before,str(ROOT),read_account=suspension_read_equal)")
    text = once(text, "previous+[e],after,str(ROOT))", "previous+[e],after,str(ROOT),read_account=suspension_read_equal)")
    text = once(text, "        require(x==z,'suspension changed during controller observation')",
                "        require(suspension_read_equal(first,current),'suspension changed during controller observation')")
    text = once(text, "        x=json.loads(json.dumps(first));z=json.loads(json.dumps(current))\n        x['pin']['metadata'].pop('atime_ns');z['pin']['metadata'].pop('atime_ns')\n", '')
    text = once(text, "        require(baseline['pin']==record('before.json')['pins'][SUSPENSION],'suspension baseline drift')",
                "        require(suspension_pin_equal(record('before.json')['pins'][SUSPENSION],baseline['pin']),'suspension baseline drift')")
    hooks = (HERE/'read-time-hooks.py').read_text()
    return once(text, "if __name__=='__main__':", hooks + "\n\nif __name__=='__main__':")


def read_time_lineage(text):
    text = once(text, 'def step(before,after,action):',
                'def step(before,after,action,read_account=None):')
    text = once(text, "        require(before==after,'suspension no-op changed')",
                "        require(read_account(before,after) if read_account else before==after,'suspension no-op changed')")
    text = once(text, 'def chain(baseline,records,current,cwd,terminal=False):',
                'def chain(baseline,records,current,cwd,terminal=False,read_account=None):')
    text = once(text, "        require(record['before']==previous,'suspension predecessor drift')",
                "        require(read_account(previous,record['before']) if read_account else record['before']==previous,'suspension predecessor drift')")
    text = once(text, "        step(record['before'],record['after'],action)",
                "        step(record['before'],record['after'],action,read_account)")
    text = once(text, "    require(previous==current,'unrecorded suspension mutation')",
                "    require(read_account(previous,current) if read_account else previous==current,'unrecorded suspension mutation')")
    return text


def read_time_routes(text):
    text = once(text, 'def validate_event(event,name,r,p,revisions,argv):',
                'def validate_event(event,name,r,p,revisions,argv,read_account=None):')
    text = once(text, "    return r.compare_routes(event['before'],event['after'],bounds)",
                "    after = read_account(event['before'],event['after'],bounds,regenerated=True) if read_account else event['after']\n    return r.compare_routes(event['before'],after,bounds)")
    text = once(text, 'def project(before,after,events,r,p,revisions,argv):',
                'def project(before,after,events,r,p,revisions,argv,read_account=None):')
    text = once(text, "    for snapshot,rows in ((a,first),(z,last)):\n        require(snapshot['directories']['runtime_children']['.beads']['routes.jsonl']==rows[city]['metadata']\n            and snapshot['directories']['city']['.beads']==rows[city]['parent'],'route snapshot mirror')", """    mirror_window=p.bounds(before['cache_access_clock'],after['cache_access_clock'])
    for snapshot,rows in ((a,first),(z,last)):
        mirror=copy.deepcopy(rows)
        mirror[city]['parent']=snapshot['directories']['city']['.beads']
        aligned=read_account(mirror,rows,mirror_window) if read_account else rows
        require(snapshot['directories']['runtime_children']['.beads']['routes.jsonl']==rows[city]['metadata']
            and snapshot['directories']['city']['.beads']==aligned[city]['parent'],'route snapshot mirror')""")
    text = once(text, "        require(event['before']==cursor,'route event preimage gap')",
                "        gap=p.bounds(previous_clock,event['before_clock'])\n        preimage=read_account(cursor,event['before'],gap) if read_account else event['before']\n        require(preimage==cursor,'route event preimage gap')")
    text = once(text, '        changes=validate_event(event,name,r,p,revisions,argv)',
                '        changes=validate_event(event,name,r,p,revisions,argv,read_account)')
    text = once(text, "    require(cursor==last,'unobserved generated route mutation')",
                "    gap=p.bounds(previous_clock,after['cache_access_clock'])\n    final=read_account(cursor,last,gap) if read_account else last\n    require(cursor==final,'unobserved generated route mutation')")
    text = once(text, '    return a,z,dict(reloads=end[len(start):],changes=proof)',
                "    if read_account:\n        # Every intervening parent read delta was independently accounted above.\n        z['directories']['city']['.beads']['atime_ns']=a['directories']['city']['.beads']['atime_ns']\n    return a,z,dict(reloads=end[len(start):],changes=proof)")
    return text


def read_time_wrapper(text):
    text = once(text, '    first_routes=routes.capture_routes(w,o)',
                '    read_start=dict(start=clock_sample(),end=clock_sample())\n    first_routes=routes.capture_routes(w,o)')
    text = once(text, "    w.require(first_routes==value['generated_routes'],'routes changed during snapshot')",
                "    read_end=dict(start=clock_sample(),end=clock_sample())\n    aligned=w.route_read_account(first_routes,value['generated_routes'],p.bounds(read_start,read_end))\n    w.require(first_routes==aligned,'routes changed during snapshot')")
    text = once(text, '    original_preservation(a,z,city_pin,receipt_pin)',
                "    original_preservation(a,z,city_pin,receipt_pin,read_window=accounting['window'])")
    text = once(text, "routes_policy.project(before,after,events,routes,p,w.REVISION,w.GC+['reload','--json'])",
                "routes_policy.project(before,after,events,routes,p,w.REVISION,w.GC+['reload','--json'],read_account=w.route_read_account)")
    old = "routes_policy.validate_event(event,name,routes,p,w.REVISION,w.GC+['reload','--json'])"
    assert text.count(old) == 2
    return text.replace(old, old[:-1]+',read_account=w.route_read_account)')


def common(text):
    text = text.replace('Template common git', 'Operations common Git')
    raw = (HERE/'common-config-exceptions.json').read_bytes()
    assert sha(raw) == '5b2f7a167ffadb8879d859121b4a4cfbc44e79d1a5615950df0bdf73ed65e8b2', 'approved config exception manifest'
    exceptions = json.loads(raw)
    assert len(exceptions) == 44
    # Embed immutable pins into the reviewed executable, not a live sidecar.
    text = once(text, 'LIMIT=1<<30', 'LIMIT=1<<30\n\n# Operator-approved exact baseline only. No permission is changed.\nCONFIG_EXCEPTIONS = '+repr(exceptions))
    text = replace_function(text, 'entry', '''def entry(path):
    path=Path(path)
    s=path.lstat()
    value=dict(mode=stat.S_IMODE(s.st_mode),type=stat.S_IFMT(s.st_mode),uid=s.st_uid,gid=s.st_gid)
    assert s.st_uid==s.st_gid==1000, 'common Git authority'
    try:relative=str(path.relative_to(COMMON))
    except ValueError:relative=None
    exception=CONFIG_EXCEPTIONS.get(relative)
    if exception is None:
        assert not s.st_mode&0o022, 'common Git authority'
    else:
        assert value=={key:exception[key] for key in value}, 'common Git exception metadata'
    if stat.S_ISREG(s.st_mode):
        assert s.st_size<=LIMIT and s.st_nlink==1, 'common Git file bound or links'
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOATIME|os.O_CLOEXEC)
        try:
            assert os.fstat(fd)==s, 'common Git open race'
            h=hashlib.sha256();size=0
            while block:=os.read(fd,1048576):
                size+=len(block);assert size<=LIMIT, 'common Git read overflow';h.update(block)
            assert os.fstat(fd)==s and path.lstat()==s and size==s.st_size, 'common Git changed during read'
        finally:os.close(fd)
        value.update(size=size,nlink=s.st_nlink,sha256=h.hexdigest())
    elif stat.S_ISLNK(s.st_mode):
        raise AssertionError('common Git symlink requires review')
    else:assert stat.S_ISDIR(s.st_mode), 'common Git special file'
    if exception is not None:assert value==exception, 'common Git exception content or links'
    return value''')
    text = once(text, '    return out\n\ndef plain(',
        "    assert CONFIG_EXCEPTIONS.keys()<=out.keys(), 'common Git exception missing'\n    return out\n\ndef plain(")
    text = replace_function(text, 'plain', '''def plain(path):
    if not os.path.lexists(path):return None
    s=path.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_size<=LIMIT and s.st_nlink==1, 'common Git plain input'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_NOATIME|os.O_CLOEXEC)
    try:
        assert os.fstat(fd)==s
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(LIMIT+1)
        assert len(raw)==s.st_size and os.fstat(fd)==s and path.lstat()==s
    finally:os.close(fd)
    return raw.decode('utf-8','strict')''')
    return text


def close(text):
    text=text.replace('Identity is the base\nactive_epoch() check.',
        'Host identity uses active_epoch. Worker identity is separately persisted before\nany drain or close and remains exact across polls and recovery invocations.')
    start=text.index('    def open_sessions():')
    end=text.index("    w.save('session.json', dict(session=session))",start)
    text=text[:start]+'''    contract=w.contract()
    identity_path=VAR/'ga-e0t1.20-close-session.json'
    def census():
        return json.loads(run('sessions',w.GC+['session','list','--json'])['stdout'])
    initial=census()
    w.require(initial.get('ok') is True and isinstance(initial.get('sessions'),list)
        and len(initial['sessions'])<=1,'close initial census')
    first=initial['sessions']
    observed=contract.close_identity(first[0]) if first else None
    if os.path.lexists(identity_path):
        binding=json.loads(w.read(identity_path))
        w.require(set(binding)=={'schema','task','session'}
            and binding['schema']=='ga-e0t1.20.close-session.v1' and binding['task']==contract.TASK,
            'close persistent binding shape')
        expected=binding['session']
        if expected is not None:w.require(contract.close_identity(expected)==expected,'close binding identity')
    else:
        expected=observed
        binding=dict(schema='ga-e0t1.20.close-session.v1',task=contract.TASK,session=expected)
        fd=os.open(identity_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:
            json.dump(binding,out,sort_keys=True);out.flush();os.fsync(out.fileno())
        parent_fd=os.open(VAR,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:os.fsync(parent_fd)
        finally:os.close(parent_fd)
    contract.close_census(initial,expected)
    release=VAR/'ga-e0t1.20-startup-release-20260927-r1/proof.json'
    if os.path.lexists(release):
        released=json.loads(w.read(release))['session']
        w.require(contract.close_identity(released)==expected,'close differs from released session')
    if drain.exists():
        previous=json.loads(w.read(drain))
        w.require(expected is not None and previous.get('session')==expected['id'],'drain belongs to another session')
    def open_sessions():return contract.close_census(census(),expected)
    def claim_before_mutation(session):
        tasks=json.loads(run('claim',w.GC+['--rig','gascity','bd','show',contract.TASK,'--json'])['stdout'])
        w.require(isinstance(tasks,list) and len(tasks)==1,'close task cardinality')
        contract.close_claim(tasks[0],session)
    session=first[0] if first else None
''' + text[end:]
    text=once(text,'    if session and not drain.exists():\n',
        '    if session and not drain.exists():\n        claim_before_mutation(session)\n')
    text=once(text,'    if still:\n', '    if still:\n        claim_before_mutation(still[0])\n')
    return text


def integrity_providers(text):
    text=once(text,
        "# M9 pinned the candidate wrapper as a second claude provider, keyed by path; M10 (file 2b902a83) keeps it.",
        "# Exact M12 adds the Template candidate wrapper. Manifest digest remains mandatory.")
    text=once(text,"['claude-native','codex','claude','claude'],'provider inventory'",
        "['claude-native','codex','claude','claude','claude'],'provider inventory'")
    text=once(text,
        "'/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker']\n        and providers[3]['sha256']=='e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3',\n        'M9 provider pins')",
        "'/home/loucmane/gas-city-template/bin/gct-claude-candidate-worker',\n        '/home/loucmane/gas-city-template/bin/gct-claude-template-candidate-worker']\n        and providers[3]['sha256']=='e4442971fd3188208eaf22974aaaf55f949b8f51041775f041ecb00a66de92a3'\n        and providers[4]['sha256']=='229d33557326abc8bafceadb06ae12ba2a2d9189e137ff0e1378d35dcf69491c',\n        'M12 provider pins')")
    return text


def assemble(final=False):
    names = git('ls-tree', '-r', '--name-only', SOURCE, OLD).decode().splitlines()
    names = [name for name in names if (name.endswith('.py') and '/generators/' not in name
             and not name.endswith(('test_successor.py','prep-r11.py','worktree-task-r1.py')))
             or ('/operator/' in name and name.endswith('.sh') and not name.endswith(('PREP.sh','WORKTREE.sh')))]
    sources = {name[len(OLD)+1:]: git('show', SOURCE+':'+name) for name in names}
    out = {}
    for name, raw in sources.items():
        text = rebind(name, raw.decode())
        if name == 'window-base-r11.py': text = read_time_base(base(text))
        elif name == 'window-r11.py': text = read_time_wrapper(text)
        elif name == 'route-chain-r1.py': text = read_time_routes(text)
        elif name == 'bind-task-r5.py': text = bind(text)
        elif name == 'route-task-r5.py': text = route(text)
        elif name == 'watch-r11.py': text = watch(text)
        elif name == 'common-snapshot-r1.py': text = common(text)
        elif name == 'close-r11.py': text = close(text)
        elif name in ('observe-integrity-r11.py','observe-terminal-r11.py'):
            text = integrity_providers(text)
        elif name == 'suspension-lineage.py': text = read_time_lineage(text.replace("'gas-city-template'", "'gascity'"))
        elif name == 'audit-queue-r3.py':
            text = text.replace("('template', ['--rig', 'gascity'])", "('gascity', ['--rig', 'gascity'])")
            text = text.replace("store=='template'", "store=='gascity'")
            text = text.replace("r['name'] != 'gas-city-template'", "r['name'] != 'gascity'")
        elif name == 'hold-r11.py': text = text.replace("r['name'] == 'gas-city-template'", "r['name'] == 'gascity'")
        if name.endswith('.sh'):
            # No draft wrapper can run, even if somebody tries to submit it.
            text = once(text, '#!/bin/sh\n', '#!/bin/sh\necho "DRAFT ONLY - not admitted for execution" >&2\nexit 125\n')
        out[name] = text.encode()
    for name in ('contract.py','test_contract.py','task-own-fields.json','worker-startup.py','WORKER-BRIEF.md',
                 'candidate-inspect.py','startup-validation.py','startup-release.py','read-time-accounting.py'):
        out[name] = (HERE/name).read_bytes()
    # The first PREFLIGHT consumed its root but never staged. Preserve it and
    # bind every successor consumer to the fresh window, without rebinding BIND.
    out = {name: raw.replace(b'/var/tmp/ga-e0t1.20-window-20260927-r1',
                             b'/var/tmp/ga-e0t1.20-window-20260928-r2') for name, raw in out.items()}
    # The inspector runs only after TERMINAL and before any coordinator Git or
    # workflow operation. This wrapper retains the same deliberate draft barrier.
    inspect_wrapper=out['operator/WATCH-1.sh'].decode()
    inspect_wrapper=inspect_wrapper.replace('WATCH-1', 'INSPECT').replace('watch-1-', 'inspect-')
    inspect_wrapper=inspect_wrapper.replace('step watch "$C/watch-r11.py" "$WATCH_SHA"',
        'step inspect "$C/candidate-inspect.py" "$WATCH_SHA"')
    inspect_wrapper=re.sub(r'^WATCH_SHA=[0-9a-f]{64}$','WATCH_SHA=ASSEMBLY_INSPECT_SHA',inspect_wrapper,flags=re.M)
    out['operator/INSPECT.sh']=inspect_wrapper.encode()
    release_wrapper=out['operator/WATCH-1.sh'].decode()
    release_wrapper=release_wrapper.replace('WATCH-1', 'RELEASE').replace('watch-1-', 'release-')
    release_wrapper=release_wrapper.replace('step watch "$C/watch-r11.py" "$WATCH_SHA"',
        'step release "$C/startup-release.py" "$WATCH_SHA"')
    release_wrapper=re.sub(r'^WATCH_SHA=[0-9a-f]{64}$','WATCH_SHA=ASSEMBLY_RELEASE_SHA',release_wrapper,flags=re.M)
    out['operator/RELEASE.sh']=release_wrapper.encode()
    if final:
        for name,raw in out.items():
            text=raw.decode()
            if name.endswith('.sh'):
                text=once(text,'echo "DRAFT ONLY - not admitted for execution" >&2\nexit 125\n','')
            elif name=='window-base-r11.py':
                text=once(text,"    require(False, 'DRAFT package has no execution admission')\n",'')
                text=once(text,'CACHE_PINNED_NS = None  # Exact new disposition still requires review and authority.',
                    'CACHE_PINNED_NS = '+str(FINAL_CACHE_NS)+'\n# Read-only observation SHA-256 '+FINAL_OBSERVATION_SHA)
            elif name in ('bind-task-r5.py','route-task-r5.py'):
                text=once(text,"    raise RuntimeError('DRAFT package has no execution admission')\n",'')
            out[name]=text.encode()
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
        tokens = {'ASSEMBLY_BASE_SHA':sha(out['window-base-r11.py']),
                  'ASSEMBLY_COMMON_SHA':sha(out['common-snapshot-r1.py']),
                  'ASSEMBLY_TERMINAL_SHA':sha(out['observe-terminal-r11.py']),
                  'ASSEMBLY_CLOSE_SHA':sha(out['close-r11.py']),
                  'ASSEMBLY_INSPECT_SHA':sha(out['candidate-inspect.py']),
                  'ASSEMBLY_VALIDATOR_SHA':sha(out['startup-validation.py']),
                  'ASSEMBLY_PROBE_SHA':sha(out['worker-startup.py']),
                  'ASSEMBLY_READ_TIME_SHA':sha(out['read-time-accounting.py']),
                  'ASSEMBLY_RELEASE_SHA':sha(out['startup-release.py'])}
        def replace_bindings(name,raw):
            text=raw.decode()
            if name=='route-task-r5.py':
                text=re.sub(r"^BIND_SHA='[^']+'$", "BIND_SHA='COMPLETED_BIND_EXECUTOR_SHA'",text,flags=re.M)
            for key,value in tokens.items():text=text.replace(key,value)
            text=HEX.sub(lambda m:mapping.get(m[0],m[0]),text)
            return text.replace('COMPLETED_BIND_EXECUTOR_SHA',COMPLETED_BIND_EXECUTOR).encode()
        newer = {name: replace_bindings(name,raw)
                 if name.endswith(('.py','.sh')) else raw for name,raw in out.items()}
        if newer == out: break
        out = newer
    else: raise RuntimeError('source binding graph did not settle')
    for name,raw in out.items():
        if name.endswith('.py'): ast.parse(raw, filename=name)
    return sources,out


def main(output, *options):
    assert options in ((),('--execution-candidate',)), 'unknown assembly mode'
    final=bool(options)
    root=Path(output)
    assert not root.exists(), 'create-only output'
    sources,out=assemble(final=final)
    root.mkdir(mode=0o700)
    for name,raw in out.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
        path.chmod(0o755 if name.endswith('.sh') else 0o644)
    manifest=dict(schema='ga-e0t1.20.s2-assembly.v1', source_commit=SOURCE,
        source_files={name:sha(raw) for name,raw in sources.items()},
        files={name:sha(raw) for name,raw in out.items()}, execution_admitted=False,
        execution_candidate=final, cache_pin_ns=FINAL_CACHE_NS if final else None,
        baseline_observation_sha256=FINAL_OBSERVATION_SHA if final else None,
        remaining=['two independent exact-head reviews','immediate preflight','live acceptance'])
    with (root/'assembly.json').open('x') as stream: json.dump(manifest,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(output=str(root),files=len(out),execution_admitted=False)))


if __name__=='__main__': main(*sys.argv[1:])
