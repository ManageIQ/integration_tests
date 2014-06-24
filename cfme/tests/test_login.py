import pytest
from cfme import dashboard
from cfme.login import login_admin, login, logout
from cfme.login import page as login_page
from utils import conf, error

pytestmark = pytest.mark.usefixtures('browser')


@pytest.mark.smoke
def test_login():
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    login_admin()
    assert dashboard.page.is_displayed(), "Could not determine if logged in"
    logout()
    assert login_page.is_displayed()


def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    with error.expected('Sorry, the username or password you entered is incorrect.'):
        login(conf.credentials['default']['username'], "badpassword@#$")
    assert login_page.is_displayed()
