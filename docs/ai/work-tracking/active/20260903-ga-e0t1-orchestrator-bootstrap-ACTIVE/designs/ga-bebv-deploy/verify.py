"""Append-only offline custody acceptance of the ga-bebv build; no live operation.

Runs the byte-identical production validator validateMetadataCustodyBuild (metadata_custody_linux.go,
sha 87e6855e, the sequence 13 proof copy) against the real artifacts:
- the preserved incompatible build 83d098fc must be refused ("metadata custody build settings not audited");
- the live Core fce2e9a0 and both new artifacts must be accepted.
ga-bebv also binds the S1a result record and the exact signer fingerprint of the build source (the
operator-signed reviewed head f45a6262), proves from the rig repository that main 0b63856a is the
merge of f45a6262 into f3856bd1 with the same tree, and proves that no embedded pack file changed
between the live build source deefb98b and the new one, so the synthetic pack-cache keys and
materialized contents stay those of the running Core. The built binary reports commit f45a6262.
It also proves the validator file in the new source is byte-identical to the proof copy, so the
installed Core would apply the same rule.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/var/tmp/ga-bebv-build-20260927')
PROOF_SRC = Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/ga-mutg-custody-artifact-proof-20260920')
VALIDATOR_SHA = '87e6855edc2524d3568c2f7da6ebb29f8e0b7bd1e951954125ac92d947267019'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
NEW = '207a78e27fe4b470ec5926ded186813543568683cf26d7d7487e6c185d8f3e8f'
CASES = [
    ('preserved-incompatible-negative', '/var/tmp/ga-mutg-build-20260919/gc-final',
     '83d098fc6e48b912f2658955bb4180f3433ddb2a0961c40af904eb21023a0f78',
     'metadata custody build settings not audited'),
    ('live-core', '/home/loucmane/gascity/bin/gc',
     'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b', ''),
    ('new-build-a', str(ROOT / 'gc-a'), NEW, ''),
    ('new-build-b', str(ROOT / 'gc-b'), NEW, ''),
]
TEST = '''package platforminstall

import (
    "crypto/sha256"
    "debug/buildinfo"
    "fmt"
    "os"
    "testing"
)

// Only supplies the unrelated image-hash helper required to compile the
// byte-identical production file. The production validator is not rewritten.
func sha256Hex(data []byte) string { return fmt.Sprintf("%x", sha256.Sum256(data)) }

func TestActualArtifactCustodyContract(t *testing.T) {
    cases := []struct { name, path, digest, wantError string }{
CASES    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            data, err := os.ReadFile(tc.path)
            if err != nil { t.Fatal(err) }
            if sha256Hex(data) != tc.digest { t.Fatal("artifact digest drift") }
            info, err := buildinfo.ReadFile(tc.path)
            if err != nil { t.Fatal(err) }
            err = validateMetadataCustodyBuild(info)
            if tc.wantError == "" {
                if err != nil { t.Fatal(err) }
            } else if err == nil || err.Error() != tc.wantError {
                t.Fatalf("want %q, got %v", tc.wantError, err)
            }
        })
    }
}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, data):
    with (ROOT / name).open('xb') as stream:
        stream.write(data)


RESULT_SHA = '8f77877c20d60720d429c40a3d1ade6d23306c622a0c2c95b81d968a2f2dd5db'
SIGNER = 'FD5585922F5335BC378AD8D42ECF4432C7E7982D'
RIG = Path('/home/loucmane/gascity/city/rigs/gascity')
HEAD = 'f45a626213dc5b8d0b52f097d978cca56e506df0'
TREE = 'f1011adaf673937fbda1d254a53c8f0eadf17c5c'
MAIN = '0b63856a8c14ba25191ee2b338be1ac3f48385f3'
MAIN_PARENTS = ('f3856bd146995305c0c2b5f958390b3760b01e21', 'f45a626213dc5b8d0b52f097d978cca56e506df0')
LIVE_SOURCE = 'deefb98b2aed07875df31351d081fbac195cb1cd'
EMBED_ROOTS = ('internal/bootstrap/packs', 'examples')
CHANGED = ('cmd/gc/build_desired_state.go', 'cmd/gc/cmd_nudge_test.go', 'cmd/gc/cmd_session.go', 'cmd/gc/cmd_session_test.go', 'cmd/gc/cmd_start.go', 'cmd/gc/launch_guard.go', 'cmd/gc/launch_guard_test.go', 'cmd/gc/pool.go', 'cmd/gc/pool_test.go', 'cmd/gc/session_lifecycle_parallel.go', 'cmd/gc/session_lifecycle_parallel_test.go', 'cmd/gc/session_name_lookup.go', 'cmd/gc/session_reconciler.go', 'cmd/gc/session_reconciler_fork_launch_test.go', 'cmd/gc/session_reconciler_test.go', 'cmd/gc/session_scaffold_staging_test.go', 'cmd/gc/worker_handle.go', 'cmd/gc/worker_handle_test.go', 'docs/reference/config.md', 'docs/reference/schema/city-schema.json', 'docs/reference/schema/city-schema.txt', 'docs/reference/schema/pack-schema.json', 'docs/reference/schema/pack-schema.txt', 'internal/api/fake_state_test.go', 'internal/api/handler_session_chat_test.go', 'internal/api/handler_session_submit_test.go', 'internal/api/handler_sessions_test.go', 'internal/api/huma_handlers_sessions_command.go', 'internal/api/launch_guard_test.go', 'internal/api/session_runtime.go', 'internal/api/worker_factory_test.go', 'internal/config/config.go', 'internal/config/field_sync_test.go', 'internal/config/launch_command.go', 'internal/config/launch_command_test.go', 'internal/config/launch_guard.go', 'internal/config/launch_guard_test.go', 'internal/config/pack.go', 'internal/config/patch.go', 'internal/migrate/migrate.go', 'internal/migrate/migrate_test.go', 'internal/pathutil/launch_guard.go', 'internal/pathutil/launch_guard_test.go', 'internal/session/chat.go', 'internal/session/launch_guard.go', 'internal/session/launch_guard_test.go', 'internal/session/manager.go', 'internal/workdir/launch_guard.go', 'internal/workdir/launch_guard_test.go', 'internal/worker/factory.go', 'internal/worker/factory_test.go', 'internal/worker/handle.go', 'internal/worker/handle_lifecycle.go', 'internal/worker/launch_refusal_test.go', 'internal/worker/start_command_equiv_test.go')


def provenance():
    result = (ROOT / 'result.json').read_bytes()
    assert sha(result) == RESULT_SHA, 'S1a result drift'
    record = json.loads(result)
    assert record['ok'] and [a['sha256'] for a in record['artifacts']] == [NEW, NEW], 'S1a artifacts'
    assert (record['head'], record['tree'], record['main']) == (HEAD, TREE, MAIN), 'S1a identity'
    assert all(a['version']['commit'] == HEAD for a in record['artifacts']), 'artifact commit stamp'
    stderr = (ROOT / 'verify-head.stderr').read_text()
    assert f'using RSA key {SIGNER}\n' in stderr and 'Good signature from' in stderr, 'build-source signer'
    git = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', str(RIG)]
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT / 'probe-home'), 'GIT_OPTIONAL_LOCKS': '0'}

    def git_out(*args):
        return subprocess.run(git + list(args), env=env, capture_output=True, check=True).stdout.decode()

    parents = tuple(git_out('rev-parse', MAIN + '^1', MAIN + '^2').split())
    assert parents == MAIN_PARENTS, parents
    trees = git_out('rev-parse', MAIN + '^{tree}', HEAD + '^{tree}', LIVE_SOURCE + '^{tree}',
                    MAIN_PARENTS[0] + '^{tree}').split()
    assert trees[:2] == [TREE, TREE], trees
    # The live build source deefb98b attested the tree of main f3856bd1 (ga-e0t1.18 S1a).
    assert trees[2] == trees[3], trees
    changed = git_out('diff', '--name-only', LIVE_SOURCE, HEAD, '--', *EMBED_ROOTS)
    assert changed == '', 'embedded pack content changed: ' + changed
    names = git_out('diff', '--name-only', LIVE_SOURCE, HEAD).split()
    assert sorted(names) == sorted(CHANGED), names
    save('provenance.json', json.dumps({'s1a_result_sha256': RESULT_SHA, 'signer': SIGNER, 'head': HEAD,
                                        'main': MAIN, 'main_parents': list(parents), 'tree': TREE,
                                        'live_source': LIVE_SOURCE, 'changed_paths': names,
                                        'embedded_pack_paths_changed': []}, indent=2).encode())


def main():
    provenance()
    env = json.loads((ROOT / 'build-a.request.json').read_text())['environment']
    save('verifier.py', Path(__file__).read_bytes())
    validator = (PROOF_SRC / 'metadata_custody_linux.go').read_bytes()
    assert sha(validator) == VALIDATOR_SHA, 'proof validator drift'
    for tag in ('repro-source', 'repro-source-b'):
        source = (ROOT / tag / 'internal/platforminstall/metadata_custody_linux.go').read_bytes()
        assert source == validator, f'{tag} validator differs from the proven production copy'
    proof = ROOT / 'custody-proof'
    proof.mkdir(mode=0o700)
    shutil.copy2(PROOF_SRC / 'metadata_custody_linux.go', proof / 'metadata_custody_linux.go')
    rows = ''.join(f'        {{"{n}", "{p}",\n         "{d}", "{w}"}},\n' for n, p, d, w in CASES)
    (proof / 'artifact_test.go').write_text(TEST.replace('CASES', rows))
    argv = [GO, 'test', '-count=1', '-v', '.']
    run_env = dict(env, GO111MODULE='off', GOWORK='off')
    save('custody-test.request.json', json.dumps({'argv': argv, 'cwd': str(proof), 'environment': run_env},
                                                 indent=2).encode())
    result = subprocess.run(argv, cwd=proof, env=run_env, capture_output=True)
    save('custody-test.stdout', result.stdout)
    save('custody-test.stderr', result.stderr)
    save('custody-test.exit', str(result.returncode).encode())
    if result.returncode:
        raise RuntimeError('custody test failed; preserved evidence')
    for name, *_ in CASES:
        assert f'--- PASS: TestActualArtifactCustodyContract/{name} ' in result.stdout.decode(), name
    save('artifact-verification.json', json.dumps({
        'ok': True, 'schema': 'ga-bebv.custody-verification.v1', 'validator_sha256': VALIDATOR_SHA,
        'validator_unchanged_in_new_source': True, 'new_artifact_sha256': NEW,
        'accepted': [c[0] for c in CASES if not c[3]], 'refused_negative': CASES[0][0],
        'test_file_sha256': sha((proof / 'artifact_test.go').read_bytes()),
        'live_adoption': False}, indent=2).encode())
    print((ROOT / 'artifact-verification.json').read_text())


if __name__ == '__main__':
    main()
