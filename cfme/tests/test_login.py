import pytest
from cfme import dashboard, login
from utils import conf, error

pytestmark = pytest.mark.usefixtures('browser')


@pytest.yield_fixture(scope="function")
def check_logged_out():
    login.logout()
    yield
    login.logout()


@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize(
    "method", login.LOGIN_METHODS, ids=[x.__name__ for x in login.LOGIN_METHODS])
@pytest.mark.usefixtures("check_logged_out")
def test_login(method):
    """ Tests that the appliance can be logged into and shows dashboard page. """
    pytest.sel.get(pytest.sel.base_url())
    assert not pytest.sel.is_displayed(dashboard.page.user_dropdown)
    login.login_admin(submit_method=method)
    assert pytest.sel.is_displayed(dashboard.page.user_dropdown), "Could not determine if logged in"
    login.logout()
    assert login.page.is_displayed()


@pytest.mark.sauce
def test_bad_password():
    """ Tests logging in with a bad password. """
    pytest.sel.get(pytest.sel.base_url())
    with error.expected('Sorry, the username or password you entered is incorrect.'):
        login.login(conf.credentials['default']['username'], "badpassword@#$")
    assert login.page.is_displayed()
