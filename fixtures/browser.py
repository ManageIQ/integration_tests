import pytest

import utils.browser


def pytest_runtest_setup(item):
    if 'browser' not in item.fixturenames:
        return
    utils.browser.ensure_browser_open()


def pytest_unconfigure(config):
    try:
        utils.browser.browser().quit()
    except:
        pass


@pytest.fixture(scope='session')
def browser():
    return utils.browser.browser
