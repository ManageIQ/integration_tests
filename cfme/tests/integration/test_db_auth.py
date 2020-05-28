import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update

# Tests concerning database authentication
pytestmark = [test_requirements.auth]


TEST_PASSWORDS = [
    f"{fauxfactory.gen_alpha()} ",  # trailing whitespace
    f" {fauxfactory.gen_alpha()}",  # leading whitespace
    f"$#!{fauxfactory.gen_alpha()}",  # leading spec char
    f"{fauxfactory.gen_alpha(17)}",  # pw > 16 char
    "",  # blank
    fauxfactory.gen_alpha().upper(),  # uppercase char
    r"$%&'()*+,-./:;<=>?@[\]^_{|}~",  # special char only
]


@pytest.fixture
def user(appliance):
    name = fauxfactory.gen_alpha(15, start="test-user-")
    creds = Credential(principal=name, secret=fauxfactory.gen_alpha())
    user_group = appliance.collections.groups.instantiate(description="EvmGroup-vm_user")
    user = appliance.collections.users.create(
        name=name,
        credential=creds,
        groups=user_group,
    )
    yield user
    user.delete_if_exists()


@pytest.fixture
def nonexistent_user(appliance):
    name = fauxfactory.gen_alpha(15, start="test-user-")
    creds = Credential(principal=name, secret=fauxfactory.gen_alpha())
    user_group = appliance.collections.groups.instantiate(description="EvmGroup-vm_user")
    user = appliance.collections.users.instantiate(
        name=name,
        credential=creds,
        groups=user_group,
    )
    yield user


@pytest.mark.parametrize(
    "pwd",
    TEST_PASSWORDS,
    ids=["trailing_whitspace", "leading_whitespace", "spec_char", "gt_16char",
         "blank", "upper_case", "special_char_only"]
)
def test_db_user_pwd(appliance, user, pwd, soft_assert):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: Appliance
        initialEstimate: 1/6h
    """
    new_credential = Credential(principal=user.credential.principal, secret=pwd)
    if pwd:
        with update(user):
            user.credential = new_credential
        with user:
            # now make sure the user can login
            view = navigate_to(appliance.server, "LoggedIn")
            soft_assert(view.current_fullname == user.name,
                        'user full name "{}" did not match UI display name "{}"'
                        .format(user.name, view.current_fullname))
            soft_assert(user.groups[0].description in view.group_names,
                        'local group "{}" not displayed in UI groups list "{}"'
                        .format(user.groups[0].description, view.group_names))
    else:
        # blank pwd doesn't allow you to click save
        view = navigate_to(user, 'Edit')
        user.change_stored_password()
        view.fill({
            'password_txt': new_credential.secret,
            'password_verify_txt': new_credential.verify_secret
        })
        assert view.save_button.disabled
        view.cancel_button.click()


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[BZ(1632718)])
def test_login_invalid_user(appliance, nonexistent_user):
    """
    Login with invalid user
    Authentication expected to fail

    Bugzilla:
        1632718

    Polarion:
        assignee: dgaikwad
        casecomponent: Auth
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/30h
    """
    with nonexistent_user:
        # we expect the user to be unable to login
        with pytest.raises(AssertionError):
            navigate_to(appliance.server, "LoggedIn")
