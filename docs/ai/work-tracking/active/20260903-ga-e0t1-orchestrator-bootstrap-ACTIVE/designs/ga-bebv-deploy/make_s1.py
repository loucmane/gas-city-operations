"""Generate the ga-bebv S1 custody build from the executed ga-e0t1.18 build by count-checked substitutions.

  python3 -I -B make_s1.py build     s1a: build.py (offline custody build of the 0b63856a tree)

ga-bebv deploys the ga-6umo launch-parameter hotfix: Core PR 49, GitHub merge commit 0b63856a on f3856bd1,
tree f1011ada. The build source is the reviewed branch head f45a6262 itself: it is signed by the operator key
FD5585922F5335BC378AD8D42ECF4432C7E7982D (signing subkey 2ECF4432C7E7982D), passed two independent
round-5 reviews, and its tree f1011ada is byte-identical to the merge commit. No new attestation commit is
made. The build asserts that MAIN's second parent is HEAD, so the built source is exactly the merged head.

Changes from the ga-e0t1.18 build (sha 126ad49d), each asserted to occur exactly once:
- identity: root /var/tmp/ga-bebv-build-20260927, HEAD f45a6262, TREE f1011ada, MAIN 0b63856a, schema;
- the docstring names the new source;
- a new assertion that MAIN^2 is HEAD.
Every other line, including the isolated gc version probe, the audited-input function, the two-clone
reproducibility check and the tool digests, is the executed ga-e0t1.18 code.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE.parent/'ga-e0t1.18-deploy'/'build.py'
SOURCE_SHA = '126ad49d65add2733a79c976005cd5c15e9d01a1ca653d502a0ffba6c5f71a0b'
HEAD = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
MAIN = '0b63856a8c14ba25191ee2b338be1ac3f48385f3'
ROOT = '/var/tmp/ga-bebv-build-20260927'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sub(text, old, new, count=1):
    found = text.count(old)
    if found != count:
        raise SystemExit('expected %d occurrence(s) of %r, found %d' % (count, old[:80], found))
    return text.replace(old, new)


def build():
    raw = SOURCE.read_bytes()
    if sha(raw) != SOURCE_SHA:
        raise SystemExit('reviewed source drift: %s' % SOURCE)
    text = raw.decode()
    text = sub(text, '"""Offline reproducible custody build of Core main f3856bd1 (ga-e0t1.18); no installation or live operation.\n',
               '"""Offline reproducible custody build of Core main 0b63856a (ga-bebv); no installation or live operation.\n')
    text = sub(text, 'Source: the locally signed build-source commit deefb98b, whose tree af5c3f04 is byte-identical to the\n'
                     'GitHub merge commit f3856bd1 (Core PR 48 on b6843d3f, the live build tree c9f19d21). Two fresh\n',
               'Source: the operator-signed reviewed head f45a6262, whose tree f1011ada is byte-identical to the\n'
               'GitHub merge commit 0b63856a (Core PR 49 on f3856bd1, the live build tree af5c3f04). Two fresh\n')
    text = sub(text, "ROOT = Path('/var/tmp/ga-e0t1.18-build-20260926')", "ROOT = Path('%s')" % ROOT)
    text = sub(text, "HEAD = 'deefb98b2aed07875df31351d081fbac195cb1cd'", "HEAD = '%s'" % HEAD)
    text = sub(text, "TREE = 'af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'", "TREE = '%s'" % TREE)
    text = sub(text, "MAIN = 'f3856bd146995305c0c2b5f958390b3760b01e21'", "MAIN = '%s'" % MAIN)
    text = sub(text, "    run('verify-head', git + ['-C', str(RIG), 'verify-commit', HEAD], ROOT)\n",
               "    assert run('rig-main-head-parent', git + ['-C', str(RIG), 'rev-parse', MAIN + '^2'],\n"
               "               ROOT).decode().strip() == HEAD, 'MAIN is not the merge of HEAD'\n"
               "    run('verify-head', git + ['-C', str(RIG), 'verify-commit', HEAD], ROOT)\n")
    text = sub(text, "'schema': 'ga-e0t1.18.build.v1'", "'schema': 'ga-bebv.build.v1'")
    out = HERE/'build.py'
    out.write_bytes(text.encode())
    out.chmod(0o644)
    print('build.py', sha(text.encode()))


VERIFY_SOURCE = HERE.parent/'ga-e0t1.18-deploy'/'verify.py'
VERIFY_SOURCE_SHA = '485fc00c02360d9f69cf35fe65713379c02f7fe4449f02a952518652ade7aba6'
# s1b: the S1a result (build ran 2026-09-27 on ops 58ed49b1 after two SOURCE_PASS reviews).
BUILD_RESULT_SHA = '8f77877c20d60720d429c40a3d1ade6d23306c622a0c2c95b81d968a2f2dd5db'
NEW = '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
LIVE = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
SIGNER = 'FD5585922F5335BC378AD8D42ECF4432C7E7982D'
MAIN_PARENTS = ('f3856bd146995305c0c2b5f958390b3760b01e21', HEAD)
LIVE_SOURCE = 'deefb98b2aed07875df31351d081fbac195cb1cd'
# The whole source change from the live build source to the reviewed head: the ga-6umo Go files, their tests
# and the regenerated schema docs (git diff --name-only deefb98b f45a6262, 55 paths).
CHANGED = (
    'cmd/gc/build_desired_state.go', 'cmd/gc/cmd_nudge_test.go', 'cmd/gc/cmd_session.go',
    'cmd/gc/cmd_session_test.go', 'cmd/gc/cmd_start.go', 'cmd/gc/launch_guard.go', 'cmd/gc/launch_guard_test.go',
    'cmd/gc/pool.go', 'cmd/gc/pool_test.go', 'cmd/gc/session_lifecycle_parallel.go',
    'cmd/gc/session_lifecycle_parallel_test.go', 'cmd/gc/session_name_lookup.go', 'cmd/gc/session_reconciler.go',
    'cmd/gc/session_reconciler_fork_launch_test.go', 'cmd/gc/session_reconciler_test.go',
    'cmd/gc/session_scaffold_staging_test.go', 'cmd/gc/worker_handle.go', 'cmd/gc/worker_handle_test.go',
    'docs/reference/config.md', 'docs/reference/schema/city-schema.json', 'docs/reference/schema/city-schema.txt',
    'docs/reference/schema/pack-schema.json', 'docs/reference/schema/pack-schema.txt',
    'internal/api/fake_state_test.go', 'internal/api/handler_session_chat_test.go',
    'internal/api/handler_session_submit_test.go', 'internal/api/handler_sessions_test.go',
    'internal/api/huma_handlers_sessions_command.go', 'internal/api/launch_guard_test.go',
    'internal/api/session_runtime.go', 'internal/api/worker_factory_test.go', 'internal/config/config.go',
    'internal/config/field_sync_test.go', 'internal/config/launch_command.go',
    'internal/config/launch_command_test.go', 'internal/config/launch_guard.go',
    'internal/config/launch_guard_test.go', 'internal/config/pack.go', 'internal/config/patch.go',
    'internal/migrate/migrate.go', 'internal/migrate/migrate_test.go', 'internal/pathutil/launch_guard.go',
    'internal/pathutil/launch_guard_test.go', 'internal/session/chat.go', 'internal/session/launch_guard.go',
    'internal/session/launch_guard_test.go', 'internal/session/manager.go', 'internal/workdir/launch_guard.go',
    'internal/workdir/launch_guard_test.go', 'internal/worker/factory.go', 'internal/worker/factory_test.go',
    'internal/worker/handle.go', 'internal/worker/handle_lifecycle.go', 'internal/worker/launch_refusal_test.go',
    'internal/worker/start_command_equiv_test.go')


def verify():
    raw = VERIFY_SOURCE.read_bytes()
    if sha(raw) != VERIFY_SOURCE_SHA:
        raise SystemExit('reviewed source drift: %s' % VERIFY_SOURCE)
    if len(CHANGED) != 55 or len(set(CHANGED)) != 55:
        raise SystemExit('changed-path list must be the 55 reviewed paths')
    text = raw.decode()
    text = sub(text, '"""Append-only offline custody acceptance of the ga-e0t1.18 build; no live operation.\n',
               '"""Append-only offline custody acceptance of the ga-bebv build; no live operation.\n')
    text = sub(text, '- the live Core b2760ea4 and both new artifacts must be accepted.\n'
                     'ga-e0t1.18 also binds the S1a result record, the build-source signer fingerprint and parents, and proves\n'
                     'that no embedded pack file changed between the live build source and the new one, so the synthetic\n'
                     'pack-cache keys and materialized contents stay those of the running Core.\n',
               '- the live Core fce2e9a0 and both new artifacts must be accepted.\n'
               'ga-bebv also binds the S1a result record and the exact signer fingerprint of the build source (the\n'
               'operator-signed reviewed head f45a6262), proves from the rig repository that main 0b63856a is the\n'
               'merge of f45a6262 into f3856bd1 with the same tree, and proves that no embedded pack file changed\n'
               'between the live build source deefb98b and the new one, so the synthetic pack-cache keys and\n'
               'materialized contents stay those of the running Core. The built binary reports commit f45a6262.\n')
    text = sub(text, "ROOT = Path('/var/tmp/ga-e0t1.18-build-20260926')", "ROOT = Path('%s')" % ROOT)
    text = sub(text, "NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'", "NEW = '%s'" % NEW)
    text = sub(text, "    ('live-core', '/home/loucmane/gascity/bin/gc',\n"
                     "     'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489', ''),\n",
               "    ('live-core', '/home/loucmane/gascity/bin/gc',\n"
               "     '%s', ''),\n" % LIVE)
    old_prov_start = text.index("RESULT_SHA = '")
    old_prov_end = text.index("def main():\n")
    text = text[:old_prov_start] + (
        "RESULT_SHA = '%s'\n"
        "SIGNER = '%s'\n"
        "RIG = Path('/home/loucmane/gascity/city/rigs/gascity')\n"
        "HEAD = '%s'\n"
        "TREE = '%s'\n"
        "MAIN = '%s'\n"
        "MAIN_PARENTS = %r\n"
        "LIVE_SOURCE = '%s'\n"
        "EMBED_ROOTS = ('internal/bootstrap/packs', 'examples')\n"
        "CHANGED = %r\n"
        "\n\n"
        "def provenance():\n"
        "    result = (ROOT / 'result.json').read_bytes()\n"
        "    assert sha(result) == RESULT_SHA, 'S1a result drift'\n"
        "    record = json.loads(result)\n"
        "    assert record['ok'] and [a['sha256'] for a in record['artifacts']] == [NEW, NEW], 'S1a artifacts'\n"
        "    assert (record['head'], record['tree'], record['main']) == (HEAD, TREE, MAIN), 'S1a identity'\n"
        "    assert all(a['version']['commit'] == HEAD for a in record['artifacts']), 'artifact commit stamp'\n"
        "    stderr = (ROOT / 'verify-head.stderr').read_text()\n"
        "    assert f'using RSA key {SIGNER}\\n' in stderr and 'Good signature from' in stderr, 'build-source signer'\n"
        "    git = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', str(RIG)]\n"
        "    env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT / 'probe-home'), 'GIT_OPTIONAL_LOCKS': '0'}\n"
        "\n"
        "    def git_out(*args):\n"
        "        return subprocess.run(git + list(args), env=env, capture_output=True, check=True).stdout.decode()\n"
        "\n"
        "    parents = tuple(git_out('rev-parse', MAIN + '^1', MAIN + '^2').split())\n"
        "    assert parents == MAIN_PARENTS, parents\n"
        "    trees = git_out('rev-parse', MAIN + '^{tree}', HEAD + '^{tree}', LIVE_SOURCE + '^{tree}',\n"
        "                    MAIN_PARENTS[0] + '^{tree}').split()\n"
        "    assert trees[:2] == [TREE, TREE], trees\n"
        "    # The live build source deefb98b attested the tree of main f3856bd1 (ga-e0t1.18 S1a).\n"
        "    assert trees[2] == trees[3], trees\n"
        "    changed = git_out('diff', '--name-only', LIVE_SOURCE, HEAD, '--', *EMBED_ROOTS)\n"
        "    assert changed == '', 'embedded pack content changed: ' + changed\n"
        "    names = git_out('diff', '--name-only', LIVE_SOURCE, HEAD).split()\n"
        "    assert sorted(names) == sorted(CHANGED), names\n"
        "    save('provenance.json', json.dumps({'s1a_result_sha256': RESULT_SHA, 'signer': SIGNER, 'head': HEAD,\n"
        "                                        'main': MAIN, 'main_parents': list(parents), 'tree': TREE,\n"
        "                                        'live_source': LIVE_SOURCE, 'changed_paths': names,\n"
        "                                        'embedded_pack_paths_changed': []}, indent=2).encode())\n"
        "\n\n"
        % (BUILD_RESULT_SHA, SIGNER, HEAD, TREE, MAIN, MAIN_PARENTS, LIVE_SOURCE, CHANGED)) + text[old_prov_end:]
    text = sub(text, "'schema': 'ga-e0t1.18.custody-verification.v1'", "'schema': 'ga-bebv.custody-verification.v1'")
    out = HERE/'verify.py'
    out.write_bytes(text.encode())
    out.chmod(0o644)
    print('verify.py', sha(text.encode()))


if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        build()
    elif sys.argv[1:] == ['verify']:
        verify()
    else:
        raise SystemExit(__doc__)
