# auto-mark items in the perf directory with perf marker
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    # mark all perf tests here so we don't have to maintain the mark in those modules
    for item in items:
        if item.nodeid.startswith('cfme/tests/perf'):
            item.add_marker(pytest.mark.perf)
