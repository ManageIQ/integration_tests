"""
cfme main plugin

This provides the option group and disables pytest logging plugin

Also provides uncollection stats during testrun/collection
"""
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme', 'cfme: options related to cfme/miq appliances')


def pytest_configure(config):
    # also disable the pytest logging system since its triggering issues with our own
    config.pluginmanager.set_blocked('logging-plugin')


def pytest_collection_finish(session):
    from cfme.fixtures.pytest_store import store
    store.terminalreporter.write(
        "Uncollection Stats:\n", bold=True)

    for reason, value in store.uncollection_stats.items():
        store.terminalreporter.write(
            f" {reason}: {value}\n", bold=True)
    store.terminalreporter.write(
        " {} tests left after all uncollections\n".format(len(session.items)),
        bold=True)
