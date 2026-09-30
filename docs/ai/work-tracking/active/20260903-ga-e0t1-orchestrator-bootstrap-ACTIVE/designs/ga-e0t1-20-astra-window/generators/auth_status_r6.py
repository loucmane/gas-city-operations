"""Pinned Codex subscription-status grammar; no command or credential access."""
import hashlib

IDENTITY = 'Logged in using ChatGPT'
PATH_ALIAS_WARNING = ('WARNING: proceeding, even though we could not create PATH aliases: '
                      'Read-only file system (os error 30)')


def subscription_status(returncode, stdout, stderr):
    """Admit success plus only the exact local warning observed under protection.

    Unknown diagnostics, API identities, duplicate identities, failed commands
    and malformed bytes still refuse. Never include raw output in an exception.
    The caller retains its pinned executable and provider-override checks.
    """
    if type(returncode) is not int or returncode != 0:
        raise RuntimeError('subscription status command failed')
    if type(stdout) is not bytes or type(stderr) is not bytes or len(stdout) + len(stderr) > 1 << 20:
        raise RuntimeError('subscription status output bound')
    raw = stdout + stderr
    try:
        lines = raw.decode('utf-8', 'strict').strip().splitlines()
    except UnicodeError:
        raise RuntimeError('subscription status encoding') from None
    if lines not in ([IDENTITY], [PATH_ALIAS_WARNING, IDENTITY]):
        raise RuntimeError('subscription identity unproven')
    return dict(subscription_only=True, path_alias_warning=len(lines) == 2,
                status_output_sha256=hashlib.sha256(raw).hexdigest())
