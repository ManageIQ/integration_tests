import pytest
from cfme import BaseLoggedInPage, login, Credential
from cfme.configure.access_control import User
from utils import conf, error
from utils.appliance import get_or_create_current_appliance
from utils.appliance.endpoints.ui import navigate_to

pytestmark = pytest.mark.usefixtures('browser')


@pytest.mark.requirement('drift')
@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize(
    "method", login.LOGIN_METHODS)
def test_login(method):
    """ Tests that the appliance can be logged into and shows dashboard page. """
    appliance = get_or_create_current_appliance()

    login_page = navigate_to(appliance.server, 'LoginScreen')
    assert login_page.is_displayed
    login_page.login_admin(method=method)
    logged_in_page = appliance.browser.create_view(BaseLoggedInPage)
    assert logged_in_page.is_displayed
    logged_in_page.logout()
    login_page.flush_widget_cache()
    assert login_page.is_displayed


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_bad_password(request):
    """ Tests logging in with a bad password. """
    appliance = get_or_create_current_appliance()

    request.addfinalizer(lambda: navigate_to(appliance.server, 'LoginScreen'))

    login_page = navigate_to(appliance.server, 'LoginScreen')

    with error.expected("Sorry, the username or password you entered is incorrect."):
        login_page.log_in(conf.credentials['default']['username'], "badpassword@#$")
        assert login.page.is_displayed
