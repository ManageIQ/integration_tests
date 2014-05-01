"""downstream: include downstream tests by default; --exclude-downstream
to exclude them

This uses py.test's own mark expressions to enable/disable tests, so py.test will
print that tests that are deselected in its own output, e.g.::

    1 tests deselected by "-m 'not downstream'"

"""


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--exclude-downstream', dest='exclude_downstream',
                    action='store_true', default=False,
        help="Exclude tests which are marked downstream, (they're included by default)")


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__.splitlines()[0])
    # Since this is really doing the work of a mark expression, it seems
    # fitting to just modify (or add) a mark expression to do the work
    if config.option.exclude_downstream:
        if config.option.markexpr:
            config.option.markexpr = 'not downstream and (%s)' % config.option.markexpr
        else:
            config.option.markexpr = 'not downstream'
