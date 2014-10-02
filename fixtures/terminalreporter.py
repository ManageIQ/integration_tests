# FlexibleTerminalReporter is imported for backward compatibility;
# it should be imported from pytest_store
from fixtures.pytest_store import FlexibleTerminalReporter, store  # NOQA


def reporter(config=None):
    """Return a py.test terminal reporter that will write to the console no matter what

    Only useful when trying to write to the console before or during a
    :py:function:`pytest_configure <pytest:_pytest.hookspec.pytest_configure>` hook.

    """
    # config arg is accepted, but no longer needed thanks to pytest_store, so it is ignored
    return store.terminalreporter
