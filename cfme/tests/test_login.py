import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.configure.access_control import User
from cfme.utils.appliance import ViaSSUI, ViaUI
from cfme.utils import conf, error, version

pytestmark = pytest.mark.usefixtures('browser')


@test_requirements.drift
@pytest.mark.tier(1)
@pytest.mark.sauce
@pytest.mark.smoke
@pytest.mark.parametrize('context, method', [(ViaUI, 'click_on_login'),
                                             (ViaUI, 'press_enter_after_password'),
                                             (ViaUI, '_js_auth_fn'),
                                             (ViaSSUI, 'click_on_login'),
                                             (ViaSSUI, 'press_enter_after_password')])
@pytest.mark.uncollectif(lambda context: context == ViaSSUI and
                         version.current_version() == version.UPSTREAM)
def test_login(context, method, appliance):
    """ Tests that the appliance can be logged into and shows dashboard page. """

    with appliance.context.use(context):
        logged_in_page = appliance.server.login()
        assert logged_in_page.is_displayed
        logged_in_page.logout()

        logged_in_page = appliance.server.login_admin(method=method)
        assert logged_in_page.is_displayed
        logged_in_page.logout()


@test_requirements.drift
@pytest.mark.tier(2)
@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaUI])
def test_bad_password(context, request, appliance):
    """ Tests logging in with a bad password. """

    username = conf.credentials['default']['username']
    password = "badpassword@#$"
    cred = Credential(principal=username, secret=password)
    user = User(credential=cred)
    user.name = 'Administrator'
    if appliance.version.is_in_series('5.7'):
        error_message = "Sorry, the username or password you entered is incorrect."
    else:
        error_message = "Incorrect username or password"

    with appliance.context.use(context):
        with error.expected(error_message):
            appliance.server.login(user)
