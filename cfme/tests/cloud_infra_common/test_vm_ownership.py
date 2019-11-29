import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.cloud.provider import CloudProvider
from cfme.exceptions import ItemNotFound
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger

pytestmark = [
    test_requirements.ownership,
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider(
        [CloudProvider, InfraProvider],
        scope='module',
        required_fields=[['templates', 'small_template']]  # default for create_on_provider
    )
]


@pytest.fixture(scope="module")
def vm_crud_local(provider):
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate(random_vm_name(context='ownrs'), provider)
    try:
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    except KeyError:
        msg = 'Missing template for provider {}'.format(provider.key)
        logger.exception(msg)
        pytest.skip(msg)
    yield vm

    try:
        vm.cleanup_on_provider()
    except Exception:
        logger.exception('Exception deleting test vm "%s" on %s', vm.name, provider.name)


@pytest.fixture(scope="module")
def role_only_user_owned(appliance):
    appliance.server.login_admin()
    role = appliance.collections.roles.create(
        name=fauxfactory.gen_alphanumeric(25, start="role_only_user_owned_"),
        vm_restriction='Only User Owned'
    )
    yield role
    appliance.server.login_admin()
    role.delete()


@pytest.fixture(scope="module")
def group_only_user_owned(appliance, role_only_user_owned):
    group_collection = appliance.collections.groups
    group = group_collection.create(
        description=fauxfactory.gen_alphanumeric(25, start="group_only_user_owned_"),
        role=role_only_user_owned.name)
    yield group
    appliance.server.login_admin()
    group.delete()


@pytest.fixture(scope="module")
def role_user_or_group_owned(appliance):
    appliance.server.login_admin()
    role = appliance.collections.roles.create(
        name=fauxfactory.gen_alphanumeric(30, start="role_user_or_group_owned_"),
        vm_restriction='Only User or Group Owned'
    )
    yield role
    appliance.server.login_admin()
    role.delete()


@pytest.fixture(scope="module")
def group_user_or_group_owned(appliance, role_user_or_group_owned):
    group_collection = appliance.collections.groups
    group = group_collection.create(
        description=fauxfactory.gen_alphanumeric(30, start="group_user_or_group_owned_"),
        role=role_user_or_group_owned.name)
    yield group
    appliance.server.login_admin()
    group.delete()


def new_credential():
    # BZ1487199 - CFME allows usernames with uppercase chars which blocks logins
    if BZ.bugzilla.get_bug(1487199).is_opened:
        return Credential(
            principal=fauxfactory.gen_alphanumeric(start="uid").lower(),
            secret='redhat'
        )
    else:
        return Credential(principal=fauxfactory.gen_alphanumeric(start="uid"), secret='redhat')


@pytest.fixture(scope="module")
def user1(appliance, group_only_user_owned):
    user1 = new_user(appliance, group_only_user_owned)
    yield user1
    appliance.server.login_admin()
    user1.delete()


@pytest.fixture(scope="module")
def user2(appliance, group_only_user_owned):
    user2 = new_user(appliance, group_only_user_owned)
    yield user2
    appliance.server.login_admin()
    user2.delete()


@pytest.fixture(scope="module")
def user3(appliance, group_user_or_group_owned):
    user3 = new_user(appliance, group_user_or_group_owned)
    yield user3
    appliance.server.login_admin()
    user3.delete()


def new_user(appliance, group_only_user_owned):
    user = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(start="user_"),
        credential=new_credential(),
        email=fauxfactory.gen_email(),
        groups=[group_only_user_owned],
        cost_center='Workload',
        value_assign='Database'
    )
    return user


def check_vm_exists(vm_ownership):
    """ Checks if VM exists through All Instances tab.

    Args:
        vm_ownership: VM object for ownership test

    Returns:
        :py:class:`bool`
    """
    try:
        vm_ownership.find_quadicon(from_any_provider=True)
        return True
    except ItemNotFound:
        return False


@pytest.mark.rhv3
def test_form_button_validation(request, user1, provider, vm_crud_local):
    """Tests group ownership

    Metadata:
        test_flag: rbac

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    # Reset button test
    vm_crud_local.set_ownership(user=user1, click_reset=True)
    # Cancel button test
    vm_crud_local.set_ownership(user=user1, click_cancel=True)
    # Save button test
    vm_crud_local.set_ownership(user=user1)
    # Unset the ownership
    vm_crud_local.unset_ownership()


@pytest.mark.rhv2
def test_user_ownership_crud(request, user1, provider, vm_crud_local):
    """Tests user ownership

    Metadata:
        test_flag: rbac

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    # Set the ownership and checking it
    vm_crud_local.set_ownership(user=user1)
    with user1:
        assert vm_crud_local.exists, "vm not found"
    vm_crud_local.unset_ownership()
    with user1:
        assert not check_vm_exists(vm_crud_local), "vm exists! but shouldn't exist"


@pytest.mark.rhv3
def test_group_ownership_on_user_only_role(request, user2, provider, vm_crud_local):
    """Tests group ownership

    Metadata:
        test_flag: rbac

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Appliance
        initialEstimate: 1/4h
    """

    # user is only a member of a single group so it will always be the current group
    vm_crud_local.set_ownership(group=user2.groups[0])
    with user2:
        assert not check_vm_exists(vm_crud_local), "vm exists! but shouldn't exist"
    vm_crud_local.set_ownership(user=user2)
    with user2:
        assert vm_crud_local.exists, "vm exists"


@pytest.mark.rhv3
def test_group_ownership_on_user_or_group_role(request, user3, provider, vm_crud_local):
    """Tests group ownership

    Metadata:
        test_flag: rbac

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    # user is only a member of a single group so it will always be the current group
    vm_crud_local.set_ownership(group=user3.groups[0])
    with user3:
        assert vm_crud_local.exists, "vm not found"
    vm_crud_local.unset_ownership()
    with user3:
        assert not check_vm_exists(vm_crud_local), "vm exists! but shouldn't exist"


@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.meta(blockers=[BZ(1622952, forced_streams=['5.10'])])
def test_template_set_ownership(appliance, request, provider, vm_crud_local):
    """ Sets ownership to an infra template.

    First publishes a template from a VM, then tries to unset an ownership of that template,
    then sets it back and in the end removes the template.
    VM is removed via fixture.
    Tests BZ 1446801 in RHCF3-14353

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
    """

    # setup the test
    # publish a vm to a template
    template = vm_crud_local.publish_to_template(template_name=random_vm_name(context='ownrs'))
    # instantiate a user representing no owner
    user_no_owner = appliance.collections.users.instantiate(name="<No Owner>")
    # instantiate a user representing Administrator
    user_admin = appliance.collections.users.instantiate(name="Administrator")

    # run the test
    try:
        # unset ownership
        template.set_ownership(user=user_no_owner)
        # set ownership back to admin
        template.set_ownership(user=user_admin)
    finally:
        # in every case, delete template we created
        template.mgmt.delete()


@pytest.mark.manual
@test_requirements.ownership
@pytest.mark.tier(1)
def test_set_ownership_back_to_default():
    """
    Set ownership back to default value.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Set ownership of a VM to some user, for example Administrator and Submit
            2. Set ownership of that VM back to <No Owner>
            3. Repeat for group ownership
            4. Try it on template instead of VM
        expectedResults:
            1. Ownership set
            2. Ownership set
            3. Ownership set
            4. Ownership set
    Bugzilla:
        1483512
    """
    pass


@pytest.mark.manual
@test_requirements.ownership
@pytest.mark.tier(1)
def test_ownership_dropdown_values():
    """
    Test that all values are displayed on ownership user and group dropdowns

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/8h
        setup:
            1. Create a new user with new group and role
        testSteps:
            1. Navigate to testing VM
            2. Configuration -> Set Ownership
            3. Inspect user dropdown and group dropdown
        expectedResults:
            3. All possible users and groups are displayed in the dropdowns
    Bugzilla:
        1330022
    """
    pass


@pytest.mark.manual
@test_requirements.ownership
@pytest.mark.tier(1)
def test_duplicate_groups():
    """
    Verify duplicat group names are not listed when selecting multiple vms and setting ownership.

    Polarion:
        assignee: apagac
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
            1. Navigate to Infrastructure -> Provider -> Vmware
            2. select multiple vms and go to Configuration -> Set ownership
            3. Verify no duplicate group names listed.
        expectedResults:
            3. No duplicate group names listed
    """
    pass
