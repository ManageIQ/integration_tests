import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.base.ui import LoginPage
from cfme.utils import conf
from cfme.utils.appliance import ViaSSUI, ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.version import LOWEST, UPSTREAM, VersionPicker

pytestmark = pytest.mark.usefixtures('browser')


def new_cred(username, password):
    username = username or conf.credentials['default']['username']
    password = password or conf.credentials['default']['password']
    cred = Credential(principal=username, secret=password)
    return cred


def new_user_instantiate(appliance, username=None, password=None, name=None):
    cred = new_cred(username=username, password=password)
    name = name or 'Administrator'
    user = appliance.collections.users.instantiate(credential=cred, name=name)
    return user


def new_user_create(appliance, request, username=None, password=None, group=None, name=None):
    cred = new_cred(username=username, password=password)
    user_group = appliance.collections.groups.instantiate(
        description=group or "EvmGroup-vm_user"
    )
    name = name or username
    user = appliance.collections.users.create(
        name=name,
        credential=cred,
        groups=user_group
    )
    request.addfinalizer(user.delete)
    return user


@pytest.mark.rhel_testing
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
                         appliance.version == UPSTREAM)
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
# BZ 1632718 is only relevant for Chrome browser
@pytest.mark.meta(blockers=[BZ(1632718, forced_streams=['5.10'])])
def test_bad_password(context, request, appliance):
    """ Tests logging in with a bad password. """

    user = new_user_instantiate(
        appliance,
        password="badpassword@#$",
    )

    error_message = VersionPicker({
        LOWEST: "Incorrect username or password",
        '5.10': "Login failed: Unauthorized"
    }).pick(appliance.version)

    with appliance.context.use(context):
        with pytest.raises(Exception, match=error_message):
            appliance.server.login(user)
        if appliance.version >= '5.9':
            view = appliance.browser.create_view(LoginPage)
            assert view.password.read() == '' and view.username.read() == ''


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.meta(blockers=[BZ(1632718, forced_streams=['5.10'])])
def test_update_password(context, request, appliance):
    """ Test updating password from the login screen. """

    # First, create a temporary new user
    username = 'user_temp_{}'.format(fauxfactory.gen_alphanumeric(4).lower())
    user = new_user_create(
        appliance,
        request,
        username=username,
        group="EvmGroup-vm_user"
    )

    error_message = VersionPicker({
        LOWEST: "Incorrect username or password",
        '5.10': "Login failed: Unauthorized"
    }).pick(appliance.version)

    # Try to login as the new user to verify it has been created
    logged_in_page = appliance.server.login(user)
    assert logged_in_page.is_displayed
    logged_in_page.logout()

    # Now try to login while changing the password for the user
    changed_pass_page = appliance.server.update_password(new_password='changeme', user=user)
    assert changed_pass_page.is_displayed
    changed_pass_page.logout()

    # Try to login with the user with old password
    with pytest.raises(Exception, match=error_message):
        appliance.server.login(user)

    # Now try changing password with invalid default password
    user2 = new_user_instantiate(
        appliance,
        username=username,
        password="made_up_invalid_pass"
    )
    with pytest.raises(Exception, match=error_message):
        appliance.server.update_password(new_password='changeme', user=user2)

    # Workaround for emptying the password fields.
    # If this wasn't here, we would change the password for admin user while
    # deleting our user. Which is bad.
    appliance.server.browser.refresh()

    # The user we created will be deleted via finalizer
