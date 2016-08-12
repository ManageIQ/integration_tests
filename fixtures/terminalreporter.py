# FlexibleTerminalReporter is imported for backward compatibility;
# it should be imported from pytest_store
from __future__ import unicode_literals
from fixtures.pytest_store import store
from utils import diaper
from utils.log import logger


def reporter(config=None):
    """Return a py.test terminal reporter that will write to the console no matter what

    Only useful when trying to write to the console before or during a
    :py:func:`pytest_configure <pytest:_pytest.hookspec.pytest_configure>` hook.

    """
    # config arg is accepted, but no longer needed thanks to pytest_store, so it is ignored
    return store.terminalreporter


def disable():
    # Cloud be a FlexibleTerminalReporter, which is a subclass of TerminalReporter,
    # so match the type directly
    with diaper:
        store.pluginmanager.unregister(store.terminalreporter)
        logger.debug('terminalreporter disabled')


def enable():
    with diaper:
        store.pluginmanager.register(store.terminalreporter, 'terminalreporter')
        logger.debug('terminalreporter enabled')
