import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.base.ui import LoginPage
from cfme.utils.appliance import ViaSSUI, ViaUI
from cfme.utils import conf, version

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
@pytest.mark.uncollectif(lambda context, appliance: context == ViaSSUI and
                         appliance.version == version.UPSTREAM)
def test_login(context, method, appliance):
    """ Tests that the appliance can be logged into and shows dashboard page.

    Polarion:
        assignee: mpusater
        caseimportance: low
        initialEstimate: 1/4h
    """

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
    """ Tests logging in with a bad password.

    Polarion:
        assignee: mpusater
        caseimportance: medium
        initialEstimate: 1/6h
    """

    username = conf.credentials['default']['username']
    password = "badpassword@#$"
    cred = Credential(principal=username, secret=password)
    user = appliance.collections.users.instantiate(credential=cred, name='Administrator')
    if appliance.version.is_in_series('5.7'):
        error_message = "Sorry, the username or password you entered is incorrect."
    else:
        error_message = "Incorrect username or password"

    with appliance.context.use(context):
        with pytest.raises(Exception, match=error_message):
            appliance.server.login(user)
        if appliance.version >= '5.9':
            view = appliance.browser.create_view(LoginPage)
            assert view.password.read() == '' and view.username.read() == ''
