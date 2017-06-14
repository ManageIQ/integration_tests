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


def pytest_runtest_setup(item):
    if item.config.option.sauce:
        browser_webdriver = conf.env['browser'].get('webdriver_options', {})
        browser_webdriver.get('desired_capabilities', {})['name'] = item.name
        browser.manager = browser.BrowserManager.from_conf()
        browser.ensure_browser_open()


def pytest_runtest_teardown(item):
    if item.config.option.sauce:
        browser.quit()
