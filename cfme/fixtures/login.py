import pytest
from utils.browser import ensure_browser_open, quit
from cfme.login import login_admin


def recycle():
    quit()
    ensure_browser_open()
    login_admin()


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
        # If we find a web driver exception, we can recycle the browser as long
        # as it is a jquery error as we know about those
        if "jquery" not in str(e).lower():
            raise
        recycle()
    except pytest.sel.NoSuchElementException as e:
        # We have also seen instances where the page gets stuck on something other
        # than the login page, and gobbles tests, this is an attempt to fix that
        recycle()

    yield browser()
