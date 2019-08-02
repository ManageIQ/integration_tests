import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.base.ui import LoginPage
from cfme.utils import conf
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.version import UPSTREAM

pytestmark = pytest.mark.usefixtures('browser')


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
    """ Tests that the appliance can be logged into and shows dashboard page.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/8h
        tags: rbac
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
# BZ 1632718 is only relevant for Chrome browser
@pytest.mark.meta(blockers=[BZ(1632718)])
def test_bad_password(context, request, appliance):
    """ Tests logging in with a bad password.

    Polarion:
        assignee: apagac
        casecomponent: WebUI
        initialEstimate: 1/8h
        tags: rbac
    """

    username = conf.credentials['default']['username']
    password = "badpassword@#$"
    cred = Credential(principal=username, secret=password)
    user = appliance.collections.users.instantiate(credential=cred, name='Administrator')

    with appliance.context.use(context):
        with pytest.raises(Exception, match="Login failed: Unauthorized"):
            appliance.server.login(user)
        view = appliance.browser.create_view(LoginPage)
        assert view.password.read() == '' and view.username.read() == ''


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.meta(blockers=[BZ(1632718)])
def test_update_password(context, request, appliance):
    """ Test updating password from the login screen.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        initialEstimate: 1/6h
    """

    # First, create a temporary new user
    username = 'user_temp_{}'.format(fauxfactory.gen_alphanumeric(4).lower())
    new_creds = Credential(principal=username, secret='redhat')
    user_group = appliance.collections.groups.instantiate(description="EvmGroup-vm_user")
    user = appliance.collections.users.create(
        name=username,
        credential=new_creds,
        groups=user_group
    )
    error_message = "Login failed: Unauthorized"

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
    new_cred = Credential(principal=username, secret="made_up_invalid_pass")
    user2 = appliance.collections.users.instantiate(credential=new_cred, name=username)
    with pytest.raises(Exception, match=error_message):
        appliance.server.update_password(new_password='changeme', user=user2)

    # Workaround for emptying the password fields.
    # If this wasn't here, we would change the password for admin user while
    # deleting our user. Which is bad.
    appliance.server.browser.refresh()

    # Delete the user we created
    user.delete()


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_pwd_trailing_whitespace():
    """
    Test changing password to one with trailing whitespace.

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_pwd_special_chars():
    """
    Test password with special characters.

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_pwd_blank():
    """
    Test changing password to a blank one.
    Test creating user with a blank password.

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_pwd_16_chars():
    """
    Password > 16 char

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_login_invalid_user():
    """
    Login with invalid user
    Authentication expected to fail, check audit.log and evm.log for
    correct log messages.

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: low
        caseposneg: negative
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@test_requirements.auth
@pytest.mark.tier(2)
def test_pwd_leading_whitespace():
    """
    Password with leading whitespace

    Polarion:
        assignee: apagac
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/8h
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_credentials_change_password_with_special_characters():
    """
    Password with only special characters

    Polarion:
        assignee: apagac
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/8h
        tags: rbac
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
@test_requirements.multi_region
@pytest.mark.parametrize('context', [ViaUI])
def test_multiregion_displayed_on_login(context):
    """
    This test case is to check that Global/Remote region is displayed on login page

    Polarion:
        assignee: izapolsk
        initialEstimate: 1/10h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.11
        casecomponent: WebUI
        testSteps:
            1. Take two or more appliances
            2. Configure DB manually
            3. Make one appliance as Global region and others are Remote
        expectedResults:
            1.
            2.
            3. Global is displayed on login page of appliance in Global region and Remote for others
    """
    pass
