import pytest
from utils.browser import ensure_browser_open
from cfme.login import login_admin


@pytest.yield_fixture(scope='function')
def logged_in(browser):
    """
    Logs into the system as admin and then returns the browser object.

    Args:
        browser: Current browser object.

    Yields: Browser object
    """
    ensure_browser_open()
    login_admin()
    yield browser()
