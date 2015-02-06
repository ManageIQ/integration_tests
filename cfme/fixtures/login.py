import pytest
from utils.browser import ensure_browser_open, quit
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
    try:
        login_admin()
    except pytest.sel.WebDriverException as e:
        if "jquery" not in str(e).lower():
            raise  # Something we don't know yet
        quit()
        ensure_browser_open()
        # And try again
        login_admin()
    yield browser()
