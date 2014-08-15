"""long_running: deselect long-running tests by default; --long-running to select them

Long-running tests with this mark applied will be deselected by default, unless
``--long-running`` is passed on the py.test command-line.

This uses py.test's own mark expressions to enable/disable tests, so py.test will
print that tests that are deselected in its own output, e.g.::

    1 tests deselected by "-m 'not long_running'"

Long-running tests are run as early as possible in the test run to prevent parallelized
test runs from running a long-running test toward the end of the suite, when the other
test nodes have shut down

"""

# XXX: Test reordering takes place in markers.smoke


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--long-running', dest='long_running', action='store_true', default=False,
        help="Run tests with the 'long_running' mark (they're skipped by default)")


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__.splitlines()[0])
    # Since this is really doing the work of a mark expression, it seems
    # fitting to just modify (or add) a mark expression to do the work
    if not config.option.long_running:
        if config.option.markexpr:
            config.option.markexpr = 'not long_running and (%s)' % config.option.markexpr
        else:
            config.option.markexpr = 'not long_running'
