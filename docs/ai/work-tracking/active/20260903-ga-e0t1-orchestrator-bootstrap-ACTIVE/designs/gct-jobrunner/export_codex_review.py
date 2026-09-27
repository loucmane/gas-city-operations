"""Create-only native review packaging. Never files a review, queues a job or contacts a service."""
import argparse
import hashlib
import json
import os
import re
import sys

import jobrunner as J


def export(request_path, rollout_path, output_dir, commit):
    if not J.HEX40.fullmatch(commit):
        raise J.Refuse('candidate must be a full commit SHA')
    request_bytes = J.read_owned(request_path, os.getuid(), J.JOB_LIMIT, 'frozen request')
    rollout_bytes = J.read_owned(rollout_path, os.getuid(), J.TRANSCRIPT_LIMIT, 'native rollout')
    try:
        request, rollout = request_bytes.decode('utf-8'), rollout_bytes.decode('utf-8')
        first = J.strict_json(rollout.split('\n')[0])
        agent = first['payload']['id']
    except (UnicodeError, KeyError, TypeError, J.Refuse, RecursionError) as exc:
        raise J.Refuse('native rollout or request cannot be decoded') from exc
    if not isinstance(agent, str) or not J.CODEX_ID.fullmatch(agent):
        raise J.Refuse('native rollout does not name a Codex thread')
    if not re.fullmatch(r'rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-' + re.escape(agent) + r'\.jsonl',
                        os.path.basename(rollout_path)):
        raise J.Refuse('native rollout filename differs from its thread identity')
    output = os.path.join(output_dir, 'codex-%s.json' % agent)
    value = {'schema': J.CODEX_SCHEMA, 'request': request, 'rollout': rollout,
             'request_sha256': hashlib.sha256(request_bytes).hexdigest(),
             'rollout_sha256': hashlib.sha256(rollout_bytes).hexdigest()}
    J.codex_review(value, output, commit)
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True) + '\n').encode('utf-8')
    if len(raw) > J.TRANSCRIPT_LIMIT:
        raise J.Refuse('native review envelope exceeds the admission size limit')
    # Validate before creating anything. Never overwrite an earlier export, even with identical bytes.
    parent_fd = os.open(output_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.fstat(parent_fd).st_uid != os.getuid():
            raise J.Refuse('export directory must be owned by the operator')
        try:
            fd = os.open(os.path.basename(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
        except OSError as exc:
            raise J.Refuse('cannot create a new native review envelope') from exc
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    # On a write/fsync failure the partial file is evidence, not silently removed or reused.
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--rollout', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--candidate', required=True)
    args = parser.parse_args()
    try:
        print(export(args.request, args.rollout, args.output_dir, args.candidate))
    except (J.Refuse, OSError) as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
