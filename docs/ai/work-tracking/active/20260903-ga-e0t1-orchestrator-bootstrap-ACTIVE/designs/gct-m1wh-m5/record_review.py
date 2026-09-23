"""M5 in-window review recorder (part of the package since r6; the binding review covers it).

  record_review.py bindings <KIND>
      Print the exact bindings the executor will demand for KIND, computed from reports/m5/q. Writes nothing.
  record_review.py record <KIND> <first-draft.json> <second-draft.json>
      Each draft is {reviewer_id, verdict, bindings, assessment}, from one independent aegis-reviewer
      run. The recorder refuses unless both drafts say KIND, carry exactly the computed bindings, have
      a non-empty assessment, and have distinct reviewer ids. It then writes both provenance files O_EXCL
      as reports/m5-reviews/<kind>-<reviewer id>.json, then q/<kind>.json O_EXCL, and finally rechecks
      the record with the same rules as recovery_controller.review().

KIND is SOURCE_PASS, PAIRING_PASS or COMMIT_PASS. The package digest is the SHA-256 of
q/prepared.json, exactly as recovery_controller.package() requires. Nothing here touches the timer,
the city, the native CLI or a Bead.
"""
import hashlib
import os
from pathlib import Path
import re
import secrets
import sys
import types

O = '/home/loucmane/gas-city-ops-worktrees/ga-e0t1-orchestrator-bootstrap'
Q = Path(O + '/reports/m5/q')
REVIEWS = Path(O + '/reports/m5-reviews')
OBS = Path(O + '/docs/ai/work-tracking/active/20260903-ga-e0t1-orchestrator-bootstrap-ACTIVE/reports/'
           'ga-e0t1.14-rollout-r1/package-r4/resume-r4b/recovery-source-r2/observe_recovery.py')
OBS_SHA = 'f5357d222f0a2f7ceb9e1a830533f20a4868fe5f3beb247de335843b730bdd78'
# Exactly the executor value (metadata_executor.PROBE_LIMIT, set as recovery_native.PROBE_LIMIT).
PROBE_LIMIT = 36.0
KINDS = ('SOURCE_PASS', 'PAIRING_PASS', 'COMMIT_PASS')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def observer():
    raw = OBS.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == OBS_SHA, 'observer source drift')
    module = types.ModuleType('observe_recovery'); module.__file__ = str(OBS)
    exec(compile(raw, str(OBS), 'exec', dont_inherit=True), module.__dict__)
    return module


def slug(kind):
    return kind.lower().replace('_', '-')


def bindings(o, kind):
    require(kind in KINDS, 'unknown review kind')
    digest = lambda name: o.read_file(str(Q/name))[0]['sha256']
    read = lambda name: o.decode(o.read_file(str(Q/name), collect=True)[1])
    package = digest('prepared.json')
    if kind == 'SOURCE_PASS':
        prepared = read('prepared.json')
        return dict(package_sha256=package, sources=prepared['sources'],
                    manifest_file_sha256=prepared['manifest_file_sha256'])
    if kind == 'PAIRING_PASS':
        return dict(package_sha256=package, observation_result_sha256=digest('observe-result.json'),
                    after_observation_sha256=digest('after-observation.json'),
                    window_sha256=digest('window.json'), probe_limit_seconds=PROBE_LIMIT)
    return dict(package_sha256=package, acceptance_sha256=digest('committed-acceptance.json'))


def exclusive(path, data):
    """Atomic and never overwriting. The complete bytes go to a fresh temporary name, are
    fsynced, then link() publishes them. link() fails if the final name exists. A crash leaves at
    most an inert temporary file, never a partial record under the final name."""
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        temporary = '.' + path.name + '.tmp-' + secrets.token_hex(8)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        finally:
            os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)
    finally:
        os.close(parent)
    return hashlib.sha256(data).hexdigest()


def check(o, kind, expected):
    """recovery_controller.review(), restated: the record the executor will read."""
    value = o.decode(o.read_file(str(Q/(slug(kind) + '.json')), collect=True)[1])
    require(set(value) == {'verdict', 'bindings', 'reviewers'} and value['verdict'] == kind
            and value['bindings'] == expected, 'record binding')
    people = value['reviewers']
    require(len(people) == 2 and len({x['reviewer_id'] for x in people}) == 2, 'two distinct reviews')
    paths, digests, identities = set(), set(), set()
    for person in people:
        require(set(person) == {'reviewer_id', 'provenance_path', 'provenance_sha256'}
                and isinstance(person['reviewer_id'], str) and person['reviewer_id'], 'provenance fields')
        pin, data = o.read_file(person['provenance_path'], collect=True)
        require(data and pin['sha256'] == person['provenance_sha256'], 'provenance digest')
        identity = (pin['metadata']['device'], pin['metadata']['inode'])
        require(person['provenance_path'] not in paths and pin['sha256'] not in digests
                and identity not in identities, 'duplicate provenance')
        paths.add(person['provenance_path']); digests.add(pin['sha256']); identities.add(identity)
        proof = o.decode(data)
        require(set(proof) == {'reviewer_id', 'verdict', 'bindings', 'assessment'}
                and proof['reviewer_id'] == person['reviewer_id'] and proof['verdict'] == kind
                and proof['bindings'] == expected and isinstance(proof['assessment'], str)
                and proof['assessment'].strip(), 'provenance content')
    return value


def record(o, kind, drafts):
    expected = bindings(o, kind)
    require(not os.path.lexists(Q/(slug(kind) + '.json')), 'review record already written')
    proofs = []
    for draft in drafts:
        proof = o.decode(Path(draft).read_bytes())
        require(set(proof) == {'reviewer_id', 'verdict', 'bindings', 'assessment'}
                and proof['verdict'] == kind and proof['bindings'] == expected
                and isinstance(proof['reviewer_id'], str)
                and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', proof['reviewer_id'])
                and isinstance(proof['assessment'], str) and proof['assessment'].strip(), 'draft ' + draft)
        proofs.append(proof)
    require(proofs[0]['reviewer_id'] != proofs[1]['reviewer_id'], 'reviewer ids must differ')
    if not os.path.lexists(REVIEWS):
        os.mkdir(REVIEWS, 0o700)
    # Named by reviewer, so an earlier refused attempt never blocks fresh reviewers. Both paths are
    # checked before either is written, so a collision leaves nothing behind.
    paths = [REVIEWS/(slug(kind) + '-' + proof['reviewer_id'] + '.json') for proof in proofs]
    require(not any(os.path.lexists(path) for path in paths), 'provenance path already used')
    people = []
    for path, proof in zip(paths, proofs):
        people.append(dict(reviewer_id=proof['reviewer_id'], provenance_path=str(path),
                           provenance_sha256=exclusive(path, o.encoded(proof))))
    exclusive(Q/(slug(kind) + '.json'), o.encoded(dict(verdict=kind, bindings=expected, reviewers=people)))
    check(o, kind, expected)
    return people


def main():
    o = observer()
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == 'bindings':
        print(o.encoded(bindings(o, args[1])).decode())
    elif len(args) == 4 and args[0] == 'record' and args[1] in KINDS:
        print(o.encoded(dict(ok=True, kind=args[1], reviewers=record(o, args[1], args[2:]))).decode())
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
