"""Tests for the ga-e0t1.18 sequence 15 transition package. Read-only; run outside any Core window.

  python3 -m pytest -q designs/ga-e0t1.18-deploy/test_s2.py
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY = '69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f'
OLD_KEY = 'a21cc0a2fbf22c14fbe59cf508d05bcc230774f5c0d9cd386215369d43a2410a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_generator_reproduces_the_transition(tmp_path):
    out = tmp_path/'s2_transition.py'
    subprocess.run([sys.executable, '-I', '-B', str(HERE/'make_s2.py'), str(out)], check=True, capture_output=True)
    assert out.read_bytes() == (HERE/'s2_transition.py').read_bytes()


def test_identity_constants():
    text = (HERE/'s2_transition.py').read_text()
    for line in ("c.OLD='b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'",
                 "c.NEW='fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'",
                 'c.NEW_SIZE=134062284', "m['sequence']==15", "receipt['sequence']==15",
                 "commit='deefb98b2aed07875df31351d081fbac195cb1cd'", "tree='af5c3f045c1f50cd62c859f6dc58fa613e5f2f99'",
                 "blob='e6e9ac576162bcdbde8fc05ecbb1943f55f0ce41'",
                 "receipt['before']==dict(sha256=c.OLD,size=134052980,"):
        assert text.count(line) == 1, line
    assert 's14_recover' not in text and "sys.argv[1]=='recover'" not in text


def test_artifact_and_blob():
    artifact = Path('/var/tmp/ga-e0t1.18-build-20260926/gc-a')
    assert sha(artifact) == 'fce2e9a0bea6c79f257e55b6424cf9271405d58f916a1017f3c14e232ad5d13b'
    assert artifact.stat().st_size == 134062284
    blob = subprocess.run(['git', 'hash-object', '--no-filters', str(artifact)], capture_output=True, text=True,
                          check=True).stdout.strip()
    assert blob == 'e6e9ac576162bcdbde8fc05ecbb1943f55f0ce41'


def test_inventory_is_bound_and_keyed_on_69fe9a2e():
    text = (HERE/'s2_transition.py').read_text()
    assert "S14_LINKS_TSV_SHA='%s'" % sha(HERE/'live-key-links.tsv') in text
    assert "S14_MANIFESTS_TSV_SHA='%s'" % sha(HERE/'live-key-manifests.tsv') in text
    links = [line.split('\t') for line in (HERE/'live-key-links.tsv').read_text().splitlines()]
    assert len(links) == 143 and all(KEY in t and OLD_KEY not in t for _, t in links)
    manifests = [line.split('\t') for line in (HERE/'live-key-manifests.tsv').read_text().splitlines()]
    assert len(manifests) == 9
    assert {(m[1], m[3]) for m in manifests} == {('f51ef6490bbc3ae9c595b2fe0aaf5a4d825c0db4e5edbc56c59d315e6dc3cf10',) * 2}


def test_m6_preimages_are_live():
    text = (HERE/'s2_transition.py').read_text()
    for path, pin in (('/home/loucmane/gascity/city/.gc/platform/install-manifest.json',
                       "sha256='7f335ad83091a1a907b628fa5813c7daf6a530340a2ed404476797b5db90fefb'"),
                      ('/home/loucmane/gascity/city/.gc/platform/install-receipt.json',
                       "sha256='123a01818b86f977ceabab1207c57795a3780261e39599019aa37f7609febaac'")):
        assert pin in text
        assert "sha256='%s'" % sha(path) == pin


def test_live_prior_state_matches_the_admitted_forms():
    """The live Core is OLD, the shim is a7bcaa7c and the surviving watchdog maps the prior image 69d00186."""
    assert sha('/home/loucmane/gascity/bin/gc') == 'b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489'
    assert sha('/home/loucmane/gascity/city/.gc/scripts/gc-beads-bd.sh') == \
        'a7bcaa7cce9261b987bb766fba19db46cc7f4ae8d8b22b6d8059bb884d8788d2'
    images = []
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                argv = Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            if b'__gc-managed-dolt-scope-watchdog' in argv:
                images.append(sha(Path('/proc', pid, 'exe')))
    assert images == ['69d00186c098b84efe6658c03d888ce07f6d6528d6c446671b53d92f7bde89f9']


def test_accepted_binding_state():
    accepted = HERE/'accepted.json'
    text = (HERE/'s2_transition.py').read_text()
    if accepted.exists():
        value = json.loads(accepted.read_text())
        assert "ACCEPTED_SHA=%r" % value['sha256'] in text and sha(value['path']) == value['sha256']
    else:
        assert "ACCEPTED_SHA='%s'" % ('0' * 64) in text
