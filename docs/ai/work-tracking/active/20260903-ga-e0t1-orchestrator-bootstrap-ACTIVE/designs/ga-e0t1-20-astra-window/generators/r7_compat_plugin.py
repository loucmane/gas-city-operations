"""Test-only substitute the successor validator into the inherited unit corpus."""
import types
import protocol_r7


def pytest_collection_modifyitems(items):
    v=types.ModuleType('r7_validator_compat')
    exec(compile(protocol_r7.validator_source(),'<r7-validator>','exec'),v.__dict__)
    for item in items:
        if item.module.__name__=='test_startup_validation': item.module.v=v
