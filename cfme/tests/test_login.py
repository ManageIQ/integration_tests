import pytest
from cfme import dashboard, login
from utils import conf, error

pytestmark = pytest.mark.usefixtures('browser')


@pytest.mark.sauce
@pytest.mark.smoke
def test_login():
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    login.login_admin()
    assert dashboard.page.is_displayed(), "Could not determine if logged in"
    login.logout()
    assert login.page.is_displayed()


def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    with error.expected('Sorry, the username or password you entered is incorrect.'):
        login.login(conf.credentials['default']['username'], "badpassword@#$")
    assert login.page.is_displayed()


@pytest.sel.go_to('dashboard')
def test_logout(logged_in):
    """ Tests that the provider can be logged out of. """
    login.logout()
    assert login.page.is_displayed()
