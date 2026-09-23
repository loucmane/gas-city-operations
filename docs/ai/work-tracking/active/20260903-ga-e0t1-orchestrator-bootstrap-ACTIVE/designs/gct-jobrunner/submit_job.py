"""Queue one reviewed operator wrapper for the job runner (coordinator side).

Usage: python3 -B submit_job.py <job_id> <wrapper path relative to the ga-e0t1 worktree> <transcript> <transcript>

Steps:
1. Copy the two reviewer transcripts (symlinks resolved) into jobs/reviews/<HEAD>/.
2. Build the job for the current worktree HEAD.
3. Dry-run the runner's own admit() against the real git state. A job the runner would refuse never
   enters the queue.
4. Publish the job atomically: write it privately, then rename it into the queue.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('jobrunner', os.path.join(HERE, 'jobrunner.py'))
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def copy_new(source, target):
    with open(source, 'rb') as handle:
        raw = handle.read()
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)


def main(argv):
    if len(argv) != 5:
        print(__doc__)
        return 2
    job_id, wrapper, first, second = argv[1:]
    cfg = J.CONFIG
    where = J.paths(cfg)
    for name in ('queue', 'done', 'reviews', 'state'):
        os.makedirs(where[name], mode=0o700, exist_ok=True)
    commit = J.real_head(cfg)
    review_dir = os.path.join(where['reviews'], commit)
    os.makedirs(review_dir, mode=0o700, exist_ok=True)
    reviews = []
    for source in (first, second):
        target = os.path.join(review_dir, os.path.basename(os.path.realpath(source)))
        if not os.path.exists(target):
            copy_new(os.path.realpath(source), target)
        reviews.append(target)
    job = {'job_id': job_id, 'commit': commit, 'wrapper': wrapper,
           'wrapper_sha256': J.sha(os.path.join(cfg['worktree'], wrapper)), 'reviews': reviews}
    final = os.path.join(where['queue'], '%s.json' % job_id)
    if os.path.lexists(final) or any(entry.split('.')[0] == job_id for entry in os.listdir(where['done'])):
        print('job id already queued or used: %s' % job_id)
        return 1
    # Write and dry-run the job privately under state/probe/<job_id>.json (admit() needs that exact
    # name), then rename it into the queue in one atomic step. So the runner never sees a partial file.
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
    os.rename(probe, final)
    print('queued %s: %s at %s' % (job_id, wrapper, commit))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
