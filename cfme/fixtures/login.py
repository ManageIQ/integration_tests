import pytest
from cfme.login import login_admin


@pytest.yield_fixture
def logged_in(browser):
    b = browser
    login_admin()
    yield b
