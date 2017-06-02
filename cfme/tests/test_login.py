import pytest

from cfme import login, test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.base.credential import Credential
from cfme.configure.access_control import User
from utils import conf, error
from utils.appliance.implementations.ui import navigate_to

pytestmark = pytest.mark.usefixtures('browser')


@test_requirements.drift
@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize("method", login.LOGIN_METHODS)
def test_login(method, appliance):
    """ Tests that the appliance can be logged into and shows dashboard page. """

    login_page = navigate_to(appliance.server, 'LoginScreen')
    assert login_page.is_displayed
    login_page.login_admin(method=method)
    logged_in_page = appliance.browser.create_view(BaseLoggedInPage)
    assert logged_in_page.is_displayed
    logged_in_page.logout()
    login_page.flush_widget_cache()
    assert login_page.is_displayed


@test_requirements.drift
@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.smoke
def test_re_login(appliance):
    """
    Tests that the appliance can be logged into and shows dashboard page after re-login to it.
    """

    login_page = navigate_to(appliance.server, 'LoginScreen')
    assert login_page.is_displayed
    login_page.login_admin()
    logged_in_page = appliance.browser.create_view(BaseLoggedInPage)
    assert logged_in_page.is_displayed
    logged_in_page.logout()
    assert login_page.is_displayed
    # Added re-login
    login_page.login_admin()
    logged_in_page = appliance.browser.create_view(BaseLoggedInPage)
    assert logged_in_page.is_displayed
    logged_in_page.logout()
    login_page.flush_widget_cache()
    assert login_page.is_displayed


@test_requirements.drift
@pytest.mark.tier(2)
@pytest.mark.sauce
def test_bad_password(request, appliance):
    """ Tests logging in with a bad password. """

    request.addfinalizer(lambda: navigate_to(appliance.server, 'LoginScreen'))

    login_page = navigate_to(appliance.server, 'LoginScreen')

    username = conf.credentials['default']['username']
    password = "badpassword@#$"
    cred = Credential(principal=username, secret=password)
    user = User(credential=cred)
    user.name = 'Administrator'

    with error.expected("Sorry, the username or password you entered is incorrect."):
        login_page.log_in(user)
        assert login_page.is_displayed
