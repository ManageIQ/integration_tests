"""
cfme.fixtures.login
-------------------

The :py:mod:`cfme.fixtures.login` module provides a generator for logging in as admin
"""
import pytest
from cfme.login import login_admin


@pytest.yield_fixture
def logged_in(browser):
    """
    Logs into the system as admin and then returns the browser object.

    Args:
        browser: Current browser object.

    Yields: Browser object
    """
    b = browser
    login_admin()
    yield b
