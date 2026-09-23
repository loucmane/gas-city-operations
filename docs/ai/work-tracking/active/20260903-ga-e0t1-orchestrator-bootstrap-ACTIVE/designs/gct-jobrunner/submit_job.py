"""Queue one reviewed operator wrapper for the job runner (coordinator side).

Usage: python3 -B submit_job.py <job_id> <wrapper path relative to the ga-e0t1 worktree> <transcript> <transcript>

Steps:
1. Validate the job id, and refuse while the queue is non-empty or the runner is HALTED. The runner
   runs one job at a time.
2. Copy the two reviewer transcripts, symlinks resolved, into jobs/reviews/<HEAD>/agent-<id>.jsonl.
   An existing copy must be byte-identical.
3. Build the job for the current worktree HEAD.
4. Dry-run the runner's own admit() against the real git state, on a private copy under
   state/probe/. A job the runner would refuse never enters the queue.
5. Rename it into the queue. The probe and queue directories share one filesystem, so the rename is
   atomic.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('jobrunner', os.path.join(HERE, 'jobrunner.py'))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def copy_review(source, target):
    with open(source, 'rb') as handle:
        raw = handle.read()
    if os.path.lexists(target):
        with open(target, 'rb') as handle:
            if handle.read() != raw:
                raise SystemExit('NOT QUEUED: %s already exists with different bytes than %s' % (target, source))
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)


def main(argv):
    if len(argv) != 5:
        print(__doc__)
        return 2
    job_id, wrapper, first, second = argv[1:]
    if not J.JOB_ID.fullmatch(job_id):
        print('NOT QUEUED: job_id must match %s' % J.JOB_ID.pattern)
        return 2
    cfg = J.CONFIG
    where = J.paths(cfg)
    for name in ('queue', 'done', 'reviews', 'state'):
        os.makedirs(where[name], mode=0o700, exist_ok=True)
    if os.listdir(where['queue']):
        print('NOT QUEUED: the queue is not empty: %s' % sorted(os.listdir(where['queue'])))
        return 1
    if os.path.lexists(where['halted']):
        print('NOT QUEUED: the runner is HALTED; record the failure and clear %s first' % where['halted'])
        return 1
    open_jobs = J.unfinished(cfg)
    if open_jobs:
        print('NOT QUEUED: unfinished jobs need a resolution first: %s' % open_jobs)
        return 1
    if any(entry.split('.')[0] == job_id for entry in os.listdir(where['done'])):
        print('NOT QUEUED: job id already used: %s' % job_id)
        return 1
    commit = J.real_head(cfg)
    review_dir = os.path.join(where['reviews'], commit)
    os.makedirs(review_dir, mode=0o700, exist_ok=True)
    reviews = []
    for source in (first, second):
        real = os.path.realpath(source)
        # Validate before filing: a filed transcript that does not pass blocks the whole commit.
        try:
            _, prompt, verdict = J.read_review(real, commit, cfg['uid'])
        except J.Refuse as exc:
            print('NOT QUEUED: %s' % exc)
            return 1
        if verdict != 'SOURCE_PASS ' + commit or 'Wrapper: ' + wrapper not in [line.strip() for line in prompt.splitlines()]:
            print('NOT QUEUED: %s does not pass %s with an exact Wrapper line' % (real, commit))
            return 1
        target = os.path.join(review_dir, os.path.basename(real))
        copy_review(real, target)
        reviews.append(target)
    job = {'job_id': job_id, 'commit': commit, 'wrapper': wrapper,
           'wrapper_sha256': J.sha(os.path.join(cfg['worktree'], wrapper)), 'reviews': reviews}
    probe_dir = os.path.join(where['state'], 'probe')
    os.makedirs(probe_dir, mode=0o700, exist_ok=True)
    probe = os.path.join(probe_dir, '%s.json' % job_id)
    if os.path.lexists(probe):
        os.unlink(probe)
    fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(job, handle, indent=1, sort_keys=True)
    try:
        J.admit(cfg, probe, J.REAL)
    except J.Refuse as exc:
        os.unlink(probe)
        print('NOT QUEUED: %s' % exc)
        return 1
    final = os.path.join(where['queue'], '%s.json' % job_id)
    if os.listdir(where['queue']):
        os.unlink(probe)
        print('NOT QUEUED: the queue filled while checking')
        return 1
    os.rename(probe, final)
    print('queued %s: %s at %s' % (job_id, wrapper, commit))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
