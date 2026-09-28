"""Offline status grammar and exact probe-delta tests. No provider invocation."""
import ast
import hashlib

import pytest

import auth_status_r6 as auth
import auth_probe_r6 as probe

IDENTITY = (auth.IDENTITY+'\n').encode()
OBSERVED = (auth.PATH_ALIAS_WARNING+'\n'+auth.IDENTITY+'\n').encode()


def test_recorded_red_and_corrected_green():
    # Exact diagnostic observation. The old predicate refuses exit-zero
    # subscription status solely because of the local read-only warning.
    assert hashlib.sha256(OBSERVED).hexdigest() == '72118305a60fa509ac4bfac8a406509a6022f2584a36f7adf9f7bed08891a71d'
    assert OBSERVED.decode().strip() != auth.IDENTITY
    assert auth.subscription_status(0, b'', OBSERVED) == dict(subscription_only=True,
        path_alias_warning=True, status_output_sha256=hashlib.sha256(OBSERVED).hexdigest())


@pytest.mark.parametrize('stdout,stderr', [(b'', IDENTITY), (IDENTITY, b'')])
def test_existing_clean_subscription_success_is_preserved(stdout, stderr):
    assert auth.subscription_status(0, stdout, stderr)['path_alias_warning'] is False


@pytest.mark.parametrize('output', [b'', b'Logged in using an API key\n',
    IDENTITY+IDENTITY, OBSERVED+IDENTITY, OBSERVED+OBSERVED,
    IDENTITY+b'unknown diagnostic\n', b'unknown diagnostic\n'+IDENTITY,
    auth.PATH_ALIAS_WARNING.encode()+b'\n',
    auth.PATH_ALIAS_WARNING.replace('30', '13').encode()+b'\n'+IDENTITY,
    auth.PATH_ALIAS_WARNING.encode()+b'\n\n'+IDENTITY,
    IDENTITY+auth.PATH_ALIAS_WARNING.encode()+b'\n',
    b'Logged in using ChatGPT and API key\n', b'\xff'+IDENTITY,
    IDENTITY+b'\0', b'x'*(1<<20)+IDENTITY])
def test_every_other_output_refuses_without_disclosure(output):
    with pytest.raises(RuntimeError) as caught:
        auth.subscription_status(0, b'', output)
    assert str(caught.value) in ('subscription identity unproven',
        'subscription status encoding', 'subscription status output bound')


@pytest.mark.parametrize('rc', [1, -1, 2, None, False, True, 0.0, '0'])
def test_failed_or_noninteger_status_never_passes(rc):
    with pytest.raises(RuntimeError, match='command failed'):
        auth.subscription_status(rc, b'', OBSERVED)


@pytest.mark.parametrize('stdout,stderr', [('', b''), (b'', ''), (bytearray(), IDENTITY)])
def test_nonbytes_outputs_refuse(stdout, stderr):
    with pytest.raises(RuntimeError, match='output bound'):
        auth.subscription_status(0, stdout, stderr)


def test_exact_generated_probe_preserves_every_other_statement():
    old, new = probe.worker_probe()
    a, z = ast.parse(old), ast.parse(new)
    new_function = next(n for n in z.body if isinstance(n, ast.FunctionDef) and n.name == 'subscription_status')
    assert ast.dump(new_function, include_attributes=False) == ast.dump(
        next(n for n in ast.parse(open(auth.__file__).read()).body
             if isinstance(n, ast.FunctionDef)), include_attributes=False)
    z.body = [n for n in z.body if not (
        isinstance(n, ast.FunctionDef) and n.name == 'subscription_status' or
        isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id in
        ('IDENTITY','PATH_ALIAS_WARNING') for t in n.targets))]
    am = next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    zm = next(n for n in z.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    ai = next(i for i,n in enumerate(am.body) if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='lines' for t in n.targets))
    zi = next(i for i,n in enumerate(zm.body) if isinstance(n,ast.Expr)
              and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)
              and n.value.func.id=='subscription_status')
    assert ai == zi
    am.body[ai:ai+2] = []
    zm.body[zi:zi+1] = []
    assert ast.dump(a,include_attributes=False)==ast.dump(z,include_attributes=False)


def test_embedded_runtime_function_uses_the_same_acceptance():
    _, source = probe.worker_probe()
    namespace = {'__name__':'frozen_probe_fixture'}
    exec(compile(source,'worker_probe_fixture.py','exec'),namespace)
    assert namespace['subscription_status'](0,b'',OBSERVED)['subscription_only'] is True
    with pytest.raises(RuntimeError):
        namespace['subscription_status'](0,b'',b'API key\n')
