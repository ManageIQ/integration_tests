import pytest
from cfme.login import login_admin, login, logout
from cfme.login import page as login_page
from cfme import dashboard
from utils import conf

pytestmark = pytest.mark.usefixtures('browser')


def test_login():
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    login_admin()
    assert dashboard.page.is_displayed(), "Could not determine if logged in"


@pytest.sel.go_to('dashboard')
def test_logout(logged_in):
    """ Testst that the provder can be logged out of. """
    logout()
    assert login_page.is_displayed()


def test_bad_password():
    """ Tests loggin in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    try:
        login(conf.credentials['default']['username'], "badpassword@#$")
    except:
        pass
