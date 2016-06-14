"""sauce: Mark a test to run on sauce

Mark a single test to run on sauce.

"""


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--sauce', dest='sauce', action='store_true', default=False,
        help="Run tests with the sauce marker on sauce labs.")


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__.splitlines()[0])
    if config.option.sauce:
        if config.option.markexpr:
            config.option.markexpr = 'sauce and ({})'.format(config.option.markexpr)
        else:
            config.option.markexpr = 'sauce'
