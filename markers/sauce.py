"""sauce: Mark a test to run on sauce

Mark a single test to run on sauce.

"""
from utils import browser
from utils import conf


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--sauce', dest='sauce', action='store_true', default=False,
        help="Run tests with the sauce marker on sauce labs.")


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__.splitlines()[0])
    if config.option.sauce:
        conf.env['browser']['sauce'] = True
        if config.option.markexpr:
            config.option.markexpr = 'sauce and ({})'.format(config.option.markexpr)
        else:
            config.option.markexpr = 'sauce'


def pytest_runtest_setup(item):
    if item.config.option.sauce:
        conf.env['browser']['sauce'] = True
        browser_name = item.callspec.params.get('browser', 'firefox')
        conf.env['browser']['browserName'] = browser_name
        conf.env['browser']['itemName'] = item.name
        browser.ensure_browser_open()


def pytest_runtest_teardown(item):
    if item.config.option.sauce:
        browser.quit()
