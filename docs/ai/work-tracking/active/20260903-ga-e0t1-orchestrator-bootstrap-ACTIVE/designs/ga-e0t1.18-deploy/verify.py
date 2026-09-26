"""Append-only offline custody acceptance of the ga-e0t1.18 build; no live operation.

Runs the byte-identical production validator validateMetadataCustodyBuild (metadata_custody_linux.go,
sha 87e6855e, the sequence 13 proof copy) against the real artifacts:
- the preserved incompatible build 83d098fc must be refused ("metadata custody build settings not audited");
- the live Core b2760ea4 and both new artifacts must be accepted.
ga-e0t1.18 also binds the S1a result record, the build-source signer fingerprint and parents, and proves
that no embedded pack file changed between the live build source and the new one, so the synthetic
pack-cache keys and materialized contents stay those of the running Core.
It also proves the validator file in the new source is byte-identical to the proof copy, so the
installed Core would apply the same rule.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path('/var/tmp/ga-e0t1.18-build-20260926')
PROOF_SRC = Path('/home/loucmane/.local/share/gas-city-staging/ga-mutg-20260920/ga-mutg-custody-artifact-proof-20260920')
VALIDATOR_SHA = '87e6855edc2524d3568c2f7da6ebb29f8e0b7bd1e951954125ac92d947267019'
GO = '/home/loucmane/.local/share/go/1.26.7/bin/go'
NEW = 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
CASES = [
    ('preserved-incompatible-negative', '/var/tmp/ga-mutg-build-20260919/gc-final',
     '83d098fc6e48b912f2658955bb4180f3433ddb2a0961c40af904eb21023a0f78',
     'metadata custody build settings not audited'),
    ('live-core', '/home/loucmane/gascity/bin/gc',
     'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489', ''),
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


RESULT_SHA = '2233e474648da36c15ba738e5b8ce5822aa6651254a49057d63a6ea6c5bb4756'
SIGNER = 'FD5585922F5335BC378AD8D42ECF4432C7E7982D'
PARENTS = ('b6843d3f539eeebaf9d9c12e7d095d25cdee585d', '0e638e1f076195e6cddbb1e7a10aaf18cdeebb6a')
LIVE_SOURCE = '9faeabc2892d8c7133111e13ad55af66790a2ac6'
EMBED_ROOTS = ('internal/bootstrap/packs', 'examples')
CHANGED = ('cmd/gc/managed_product_dispatch_gate.go', 'cmd/gc/managed_product_dispatch_gate_test.go',
           'internal/managedworker/canary.go', 'internal/managedworker/canary_profile.go',
           'internal/managedworker/canary_profile_test.go', 'internal/platforminstall/integrity.go',
           'internal/platforminstall/integrity_test.go')


def provenance():
    result = (ROOT / 'result.json').read_bytes()
    assert sha(result) == RESULT_SHA, 'S1a result drift'
    record = json.loads(result)
    assert record['ok'] and [a['sha256'] for a in record['artifacts']] == [NEW, NEW], 'S1a artifacts'
    head = record['head']
    assert f'using RSA key {SIGNER}' in (ROOT / 'verify-head.stderr').read_text(), 'build-source signer'
    git = ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
           '-C', str(ROOT / 'repro-source')]
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT / 'probe-home'), 'GIT_OPTIONAL_LOCKS': '0'}
    parents = subprocess.run(git + ['rev-parse', head + '^1', head + '^2'], env=env, capture_output=True,
                             check=True).stdout.decode().split()
    assert tuple(parents) == PARENTS, parents
    changed = subprocess.run(git + ['diff', '--name-only', LIVE_SOURCE, head, '--', *EMBED_ROOTS],
                             env=env, capture_output=True, check=True).stdout
    assert changed == b'', 'embedded pack content changed: ' + changed.decode()
    names = subprocess.run(git + ['diff', '--name-only', LIVE_SOURCE, head], env=env,
                           capture_output=True, check=True).stdout.decode().split()
    # The whole source change is exactly the seven reviewed Go files of Core PR 48; no embedded asset.
    assert sorted(names) == sorted(CHANGED), names
    save('provenance.json', json.dumps({'s1a_result_sha256': RESULT_SHA, 'signer': SIGNER,
                                        'parents': list(parents), 'live_source': LIVE_SOURCE,
                                        'changed_paths': names, 'embedded_pack_paths_changed': []},
                                       indent=2).encode())


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
        'ok': True, 'schema': 'ga-e0t1.18.custody-verification.v1', 'validator_sha256': VALIDATOR_SHA,
        'validator_unchanged_in_new_source': True, 'new_artifact_sha256': NEW,
        'accepted': [c[0] for c in CASES if not c[3]], 'refused_negative': CASES[0][0],
        'test_file_sha256': sha((proof / 'artifact_test.go').read_bytes()),
        'live_adoption': False}, indent=2).encode())
    print((ROOT / 'artifact-verification.json').read_text())


if __name__ == '__main__':
    main()
