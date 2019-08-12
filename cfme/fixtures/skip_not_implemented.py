import pytest


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    """Pytest hook ensuring that failures caused by NotImplementedError show up as skips instead"""
    outcome = yield
    try:
        outcome.get_result()
    except NotImplementedError as e:
        pytest.skip(e)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    """Pytest hook ensuring that failures caused by NotImplementedError show up as skips instead"""
    outcome = yield
    try:
        outcome.get_result()
    except NotImplementedError as e:
        pytest.skip(e)
