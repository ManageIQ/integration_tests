import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


# Specific tests concerning ldap authentication
pytestmark = [
    test_requirements.auth,
]


@pytest.fixture
def db_user(appliance):
    name = f"test-user-{fauxfactory.gen_alpha()}"
    creds = Credential(principal=name, secret=fauxfactory.gen_alpha())
    user_group = appliance.collections.groups.instantiate(description="EvmGroup-vm_user")
    user = appliance.collections.users.create(
        name=name,
        credential=creds,
        groups=user_group,
    )
    yield user
    user.delete_if_exists()


@pytest.mark.tier(2)
@pytest.mark.provider([VMwareProvider], override=True, scope="function", selector=ONE)
@pytest.mark.usefixtures('setup_provider')
def test_validate_lookup_button_provisioning(
        appliance, provider, small_template, setup_ldap_auth_provider
):
    """
    configure ldap and validate for lookup button in provisioning form

    Polarion:
        assignee: jdupuy
        casecomponent: Auth
        caseimportance: medium
        initialEstimate: 1/4h
    """
    auth_provider = setup_ldap_auth_provider
    user = auth_provider.user_data[0]
    username = user.username.replace(" ", "-")
    domain = auth_provider.as_fill_value().get("user_suffix")

    view = navigate_to(appliance.collections.infra_vms, "Provision")
    # select the template
    view.form.fill({
        "template_name": small_template.name,
        "provider_name": provider.name,
    })
    # now enter email and lookup the first and last name
    view.form.request.fill({
        "email": f"{username}@{domain}"
    })
    # lookup the user's info
    assert not view.form.request.lookup.disabled
    view.form.request.lookup.click()
    # to see info you have to change tabs
    view.form.purpose.click()
    view.form.request.click()
    # now get the first and last name
    assert view.form.request.first_name.read() == user.fullname.split(" ")[0].lower()
    assert view.form.request.last_name.read() == user.fullname.split(" ")[1].lower()


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1632718)])
def test_verify_database_user_login_fails_with_external_auth_configured(
        appliance, setup_ldap_auth_provider, db_user
):
    """
    Login with user registered to cfme internal database.
    Authentication expected to fail

    Bugzilla:
        1632718

    Polarion:
        assignee: jdupuy
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/4h
    """
    with db_user:
        # we expect authentication to fail and to raise an AssertionError
        with pytest.raises(AssertionError):
            navigate_to(appliance.server, "LoggedIn")
