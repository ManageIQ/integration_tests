import pytest
from cfme import dashboard
from cfme.login import login_admin, login, logout
from cfme.login import page as login_page
from utils import conf

pytestmark = pytest.mark.usefixtures('browser')


def test_login():
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    login_admin()
    assert dashboard.page.is_displayed(), "Could not determine if logged in"


def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    login(conf.credentials['default']['username'], "badpassword@#$")
    expected_error = 'the username or password you entered is incorrect'
    assert login_page.is_displayed()
    assert expected_error in pytest.sel.text(login_page.flash)


@pytest.sel.go_to('dashboard')
def test_logout(logged_in):
    """ Testst that the provder can be logged out of. """
    logout()
    assert login_page.is_displayed()
