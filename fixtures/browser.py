import pytest

import utils
import utils.browser
from fixtures.navigation import home_page_logged_in


@pytest.yield_fixture(scope='module')
def browser():
    with utils.browser.browser_session() as session:
        yield session


@pytest.yield_fixture(scope='function')
def browser_funcscope():
    with utils.browser.browser_session() as session:
        yield session


@pytest.yield_fixture(scope='function')
def duckwebqa(browser_funcscope):
    # duckwebqa quacks like a mozwebqa duck
    yield utils.browser.testsetup


@pytest.yield_fixture(scope='module')
def duckwebqa_loggedin(browser):
    # On login to rule them all!
    yield home_page_logged_in(utils.browser.testsetup)
