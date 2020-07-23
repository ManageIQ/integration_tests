import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.base.ui import LoginPage
from cfme.utils import conf
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.version import UPSTREAM


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
@pytest.mark.uncollectif(lambda context, appliance:
                         context == ViaSSUI and appliance.version == UPSTREAM,
                         reason='SSUI context not valid for upstream testing')
def test_login(context, method, appliance):
    """ Tests that the appliance can be logged into and shows dashboard page.

    Polarion:
        assignee: dgaikwad
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
@pytest.mark.meta(automates=[1632718])
def test_bad_password(context, request, appliance):
    """ Tests logging in with a bad password and 1632718 is only relevant for Chrome browser

    Bugzilla:
        1632718
    Polarion:
        assignee: dgaikwad
        casecomponent: WebUI
        initialEstimate: 1/8h
        tags: rbac
    """

    username = conf.credentials['default']['username']
    password = "badpassword@#$"
    cred = Credential(principal=username, secret=password)
    user = appliance.collections.users.instantiate(credential=cred, name='Administrator')

    with appliance.context.use(context):
        with pytest.raises(
            Exception, match="Sorry, the username or password you entered is incorrect."
        ):
            appliance.server.login(user)
        view = appliance.browser.create_view(LoginPage)
        assert view.password.read() == '' and view.username.read() == ''


@pytest.mark.tier(3)
@pytest.mark.ignore_stream("5.10")
@test_requirements.multi_region
@pytest.mark.long_running
@pytest.mark.parametrize('context', [ViaUI])
def test_multiregion_displayed_on_login(context, setup_multi_region_cluster, multi_region_cluster):
    """
    This test case is to check that Global/Remote region is displayed on login page

    Polarion:
        assignee: izapolsk
        initialEstimate: 1/10h
        caseimportance: medium
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
    with multi_region_cluster.global_appliance as gapp:
        login_view = navigate_to(gapp.server, 'LoginScreen')
        assert login_view.is_displayed
        assert 'Global' in login_view.details.region.text

    with multi_region_cluster.remote_appliances[0] as rapp:
        login_view = navigate_to(rapp.server, 'LoginScreen')
        assert login_view.is_displayed
        assert 'Remote' in login_view.details.region.text


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.meta(automates=[BZ(1632718)])
@pytest.mark.browser_isolation
@test_requirements.auth
def test_update_password(context, request, appliance):
    """ Test updating password from the login screen.

    Polarion:
        assignee: jdupuy
        casecomponent: Infra
        initialEstimate: 1/6h
    """

    # First, create a temporary new user
    username = fauxfactory.gen_alphanumeric(15, start="user_temp_").lower()
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
