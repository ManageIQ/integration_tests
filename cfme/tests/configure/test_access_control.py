# -*- coding: utf-8 -*-
import traceback

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.common.provider import base_types
from cfme.configure.access_control import AddUserView
from cfme.configure.tasks import TasksView
from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.exceptions import RBACOperationBlocked
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.markers.env_markers.provider import ONE
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.update import update

pytestmark = [
    test_requirements.rbac,
    pytest.mark.provider(classes=[RHEVMProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope='module')
def group_collection(appliance):
    return appliance.collections.groups


def new_credential():
    return Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric(4)),
                      secret='redhat')


def new_user(appliance, groups, name=None, credential=None):
    name = name or 'user{}'.format(fauxfactory.gen_alphanumeric())
    credential = credential or new_credential()

    user = appliance.collections.users.create(
        name=name,
        credential=credential,
        email='xyz@redhat.com',
        groups=groups,
        cost_center='Workload',
        value_assign='Database')
    return user


def new_role(appliance, name=None):
    name = name or 'rol{}'.format(fauxfactory.gen_alphanumeric())
    return appliance.collections.roles.create(
        name=name,
        vm_restriction='None')


@pytest.fixture(scope='function')
def check_item_visibility(tag):
    def _check_item_visibility(item, user_restricted):
        item.add_tag(tag)
        with user_restricted:
            assert item.exists
        item.remove_tag(tag)
        with user_restricted:
            assert not item.exists

    return _check_item_visibility


@pytest.fixture(params=['tag', 'tag_expression'])
def tag_value(appliance, category, tag, request):
    tag_type = request.param
    if tag_type == 'tag':
        tag_for_create = ([category.display_name, tag.display_name], True)
        tag_for_update = ([category.display_name, tag.display_name], False)
    else:
        tag_for_create = 'fill_tag(My Company Tags : {}, {})'.format(category.display_name,
                                                                     tag.display_name)
        tag_for_update = 'delete_whole_expression'
    return tag_for_create, tag_for_update


@pytest.fixture(scope='module')
def catalog_obj(appliance):
    catalog_name = fauxfactory.gen_alphanumeric()
    catalog_desc = "My Catalog"

    cat = appliance.collections.catalogs.create(name=catalog_name, description=catalog_desc)
    yield cat

    if cat.exists:
        cat.delete()


# User test cases
@pytest.mark.sauce
@pytest.mark.tier(2)
def test_user_crud(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    user = new_user(appliance, [group])
    with update(user):
        user.name = "{}edited".format(user.name)
    copied_user = user.copy()
    copied_user.delete()
    user.delete()


@pytest.mark.tier(2)
def test_user_assign_multiple_groups(appliance, request, group_collection):
    """Assign a user to multiple groups

    Steps:
        * Create a user and assign them to multiple groups
        * Login as the user
        * Confirm that the user has each group visible in the Settings menu

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_names = [
        'EvmGroup-user', 'EvmGroup-administrator', 'EvmGroup-user_self_service', 'EvmGroup-desktop']

    group_list = [group_collection.instantiate(description=name) for name in group_names]

    user = new_user(appliance, groups=group_list)

    request.addfinalizer(user.delete)
    request.addfinalizer(user.appliance.server.login_admin)

    with user:
        view = navigate_to(appliance.server, 'LoggedIn')
        assigned_groups = view.group_names
        assert set(assigned_groups) == set(group_names), (
            "User {} assigned groups {} are different from expected groups {}"
            .format(user, view.group_names, group_names))


@pytest.mark.tier(2)
def test_user_change_groups(appliance, group_collection):
    """Assign a user to multiple groups and confirm that the user can successfully change groups

    Polarion:
        assignee: apagac
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    group_names = [
        'EvmGroup-super_administrator', 'EvmGroup-administrator', 'EvmGroup-approver',
        'EvmGroup-auditor', 'EvmGroup-desktop', 'EvmGroup-operator',
        'EvmGroup-security', 'EvmGroup-user', 'EvmGroup-vm_user', ]

    group_list = [group_collection.instantiate(description=name) for name in group_names]

    test_user = new_user(appliance, groups=group_list)
    with test_user:
        view = navigate_to(appliance.server, 'LoggedIn')

        orig_group = view.current_groupname

        # Set the group list order so that we change to the original group last
        group_test_list = [name for name in group_names if name != orig_group] + [orig_group]

        for group in group_test_list:
            view.change_group(group)

            assert group == view.current_groupname, (
                "User failed to change current group from {} to {}".format(
                    view.current_groupname, group))


@pytest.mark.tier(2)
def test_user_login(appliance, group_collection):
    """
    Bugzilla:
        1035399

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    user = new_user(appliance, [group])
    try:
        with user:
            navigate_to(appliance.server, 'LoggedIn')
    finally:
        user.appliance.server.login_admin()


@pytest.mark.tier(3)
def test_user_duplicate_username(appliance, group_collection):
    """ Tests that creating user with existing username is forbidden.

    Steps:
        * Generate some credential
        * Create a user with this credential
        * Create another user with same credential

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    credential = new_credential()

    nu = new_user(appliance, [group], credential=credential)
    with pytest.raises(RBACOperationBlocked):
        nu = new_user(appliance, [group], credential=credential)

    # Navigating away from this page will create an "Abandon Changes" alert
    # Since group creation failed we need to reset the state of the page
    navigate_to(nu.appliance.server, 'Dashboard')


@pytest.mark.tier(3)
def test_user_allow_duplicate_name(appliance, group_collection):
    """ Tests that creating user with existing full name is allowed.

    Steps:
        * Generate full name
        * Create a user with this full name
        * Create another user with same full name

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    name = 'user{}'.format(fauxfactory.gen_alphanumeric())

    # Create first user
    new_user(appliance, [group], name=name)
    # Create second user with same full name
    nu = new_user(appliance, [group], name=name)

    assert nu.exists


@pytest.mark.tier(3)
def test_username_required_error_validation(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    with pytest.raises(Exception, match="Name can't be blank"):
        appliance.collections.users.create(
            name="",
            credential=new_credential(),
            email='xyz@redhat.com',
            groups=[group]
        )


@pytest.mark.tier(3)
def test_userid_required_error_validation(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    with pytest.raises(Exception, match="Userid can't be blank"):
        appliance.collections.users.create(
            name='user{}'.format(fauxfactory.gen_alphanumeric()),
            credential=Credential(principal='', secret='redhat'),
            email='xyz@redhat.com',
            groups=[group]
        )
    # Navigating away from this page will create an "Abandon Changes" alert
    # Since group creation failed we need to reset the state of the page
    navigate_to(appliance.server, 'Dashboard')


@pytest.mark.tier(3)
def test_user_password_required_error_validation(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    check = "Password can't be blank"

    with pytest.raises(Exception, match=check):
        appliance.collections.users.create(
            name='user{}'.format(fauxfactory.gen_alphanumeric()),
            credential=Credential(
                principal='uid{}'.format(fauxfactory.gen_alphanumeric()), secret=None),
            email='xyz@redhat.com',
            groups=[group])
    # Navigating away from this page will create an "Abandon Changes" alert
    # Since group creation failed we need to reset the state of the page
    navigate_to(appliance.server, 'Dashboard')


@pytest.mark.tier(3)
def test_user_group_error_validation(appliance):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    with pytest.raises(Exception, match="A User must be assigned to a Group"):
        appliance.collections.users.create(
            name='user{}'.format(fauxfactory.gen_alphanumeric()),
            credential=new_credential(),
            email='xyz@redhat.com',
            groups=[''])


@pytest.mark.tier(3)
def test_user_email_error_validation(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group = group_collection.instantiate(description='EvmGroup-user')

    with pytest.raises(Exception, match="Email must be a valid email address"):
        appliance.collections.users.create(
            name='user{}'.format(fauxfactory.gen_alphanumeric()),
            credential=new_credential(),
            email='xyzdhat.com',
            groups=group)


@pytest.mark.tier(2)
@test_requirements.tag
def test_user_edit_tag(appliance, group_collection, tag):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Configuration
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    user = new_user(appliance, [group])
    user.add_tag(tag)
    assert any([
        tag_available.category.display_name == tag.category.display_name and
        tag_available.display_name == tag.display_name
        for tag_available in user.get_tags()
    ]), 'Assigned tag was not found on the details page'
    user.delete()


@pytest.mark.tier(3)
@test_requirements.tag
def test_user_remove_tag(appliance, group_collection):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)

    user = new_user(appliance, [group])
    added_tag = user.add_tag()
    user.remove_tag(added_tag)
    navigate_to(user, 'Details')
    assert not any([
        tag.category.display_name == added_tag.category.display_name and
        tag.display_name == added_tag.display_name
        for tag in user.get_tags()
    ]), 'Remove User tag failed'
    user.delete()


@pytest.mark.tier(3)
def test_delete_default_user(appliance):
    """Test for deleting default user Administrator.

    Steps:
        * Login as Administrator user
        * Try deleting the user

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    user = appliance.collections.users.instantiate(name='Administrator')
    with pytest.raises(RBACOperationBlocked):
        user.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[BZ(1090877)])
def test_current_user_login_delete(appliance, request):
    """Test for deleting current user login.

    Steps:
        * Login as Admin user
        * Create a new user
        * Login with the new user
        * Try deleting the user

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = "EvmGroup-super_administrator"
    group = group_collection(appliance).instantiate(description=group_name)

    user = new_user(appliance, [group])
    request.addfinalizer(user.delete)
    request.addfinalizer(user.appliance.server.login_admin)
    with user:
        with pytest.raises(RBACOperationBlocked):
            user.delete()


@pytest.mark.tier(3)
@test_requirements.tag
def test_tagvis_user(user_restricted, check_item_visibility):
    """ Tests if group honour tag visibility feature
    Prerequirement:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to group
        2. Login as restricted user, group is visible for user
        3. As admin remove tag from group
        4. Login as restricted user, group is not visible for user

    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    check_item_visibility(user_restricted, user_restricted)


@pytest.mark.sauce
@pytest.mark.tier(2)
# Group test cases
def test_group_crud(group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = 'EvmRole-administrator'
    group = group_collection.create(
        description='grp{}'.format(fauxfactory.gen_alphanumeric()), role=role)
    with update(group):
        group.description = "{}edited".format(group.description)
    group.delete()


@pytest.mark.sauce
@pytest.mark.tier(2)
@test_requirements.tag
def test_group_crud_with_tag(provider, tag_value, group_collection):
    """Test for verifying group create with tag defined

    Steps:
        * Login as Admin user
        * Navigate to add group page
        * Fill all fields
        * Set tag
        * Save group

    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    tag_for_create, tag_for_update = tag_value

    path = 'VM_Template-Folder' if provider.key == 'vsphere55' else 'Discovered virtual machine'

    group = group_collection.create(
        description='grp{}'.format(fauxfactory.gen_alphanumeric()),
        role='EvmRole-approver',
        tag=tag_for_create,
        host_cluster=([provider.data['name']], True),
        vm_template=([provider.data['name'], provider.data['datacenters'][0],
                     path], True)
    )
    with update(group):
        group.tag = tag_for_update
        group.host_cluster = ([provider.data['name']], False)
        group.vm_template = ([provider.data['name'], provider.data['datacenters'][0],
                             path], False)
    group.delete()


@pytest.mark.tier(3)
def test_group_duplicate_name(group_collection):
    """ Verify that two groups can't have the same name

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        tags: rbac
        casecomponent: Configuration
    """
    role = 'EvmRole-approver'
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role)

    with pytest.raises(RBACOperationBlocked):
        group = group_collection.create(
            description=group_description, role=role)

    # Navigating away from this page will create an "Abandon Changes" alert
    # Since group creation failed we need to reset the state of the page
    navigate_to(group.appliance.server, 'Dashboard')


@pytest.mark.tier(2)
@test_requirements.tag
def test_group_edit_tag(group_collection):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    role = 'EvmRole-approver'
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role)

    added_tag = group.add_tag()
    assert any([
        tag.category.display_name == added_tag.category.display_name and
        tag.display_name == added_tag.display_name
        for tag in group.get_tags()
    ]), 'Group edit tag failed'
    group.delete()


@pytest.mark.tier(2)
@test_requirements.tag
def test_group_remove_tag(group_collection):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    role = 'EvmRole-approver'
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role)

    navigate_to(group, 'Edit')
    added_tag = group.add_tag()
    group.remove_tag(added_tag)
    assert not any([
        tag.category.display_name == added_tag.category.display_name and
        tag.display_name == added_tag.display_name
        for tag in group.get_tags()
    ]), 'Remove Group User tag failed'
    group.delete()


@pytest.mark.tier(3)
def test_group_description_required_error_validation(group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    error_text = "Description can't be blank"

    with pytest.raises(Exception, match=error_text):
        group_collection.create(description=None, role='EvmRole-approver')

    # Navigating away from this page will create an "Abandon Changes" alert
    # Since group creation failed we need to reset the state of the page
    navigate_to(group_collection.parent.server, 'Dashboard')


@pytest.mark.tier(3)
def test_delete_default_group(group_collection):
    """Test for deleting default group EvmGroup-administrator.

    Steps:
        * Login as Administrator user
        * Try deleting the group EvmGroup-adminstrator

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group = group_collection.instantiate(description='EvmGroup-administrator')

    with pytest.raises(RBACOperationBlocked):
        group.delete()


@pytest.mark.tier(3)
def test_delete_group_with_assigned_user(appliance, group_collection):
    """Test that CFME prevents deletion of a group that has users assigned

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = 'EvmRole-approver'
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role)
    new_user(appliance, [group])
    with pytest.raises(RBACOperationBlocked):
        group.delete()


@pytest.mark.tier(3)
def test_edit_default_group(group_collection):
    """Test that CFME prevents a user from editing a default group

    Steps:
        * Login as Administrator user
        * Try editing the group EvmGroup-adminstrator

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group = group_collection.instantiate(description='EvmGroup-approver')

    group_updates = {}
    with pytest.raises(RBACOperationBlocked):
        group.update(group_updates)


@pytest.mark.tier(3)
def test_edit_sequence_usergroups(request, group_collection):
    """Test for editing the sequence of user groups for LDAP lookup.

    Steps:
        * Login as Administrator user
        * create a new group
        * Edit the sequence of the new group
        * Verify the changed sequence

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/8h
        tags: rbac
    """
    role_name = 'EvmRole-approver'
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role_name)
    request.addfinalizer(group.delete)

    group.set_group_order(group.description)


@pytest.mark.tier(3)
@test_requirements.tag
def test_tagvis_group(user_restricted, group_with_tag, check_item_visibility):
    """ Tests if group honour tag visibility feature
    Prerequirement:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to group
        2. Login as restricted user, group is visible for user
        3. As admin remove tag from group
        4. Login as restricted user, group is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: Tagging
        initialEstimate: 1/8h
    """
    check_item_visibility(group_with_tag, user_restricted)


# Role test cases
@pytest.mark.sauce
@pytest.mark.tier(2)
def test_role_crud(appliance):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = _mk_role(appliance, name=None, vm_restriction=None,
                    product_features=[(['Everything'], False),
                                      (['Everything', 'Settings', 'Configuration'], True),
                                      (['Everything', 'Services', 'Catalogs Explorer'], True)])
    with update(role):
        role.name = "{}edited".format(role.name)
    copied_role = role.copy()
    copied_role.delete()
    role.delete()


@pytest.mark.tier(3)
def test_rolename_required_error_validation(appliance):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    # When trying to create a role with no name, the Add button is disabled.
    # We are waiting for an Exception saying that there are no success
    # or fail messages, because the Add button cannot be clicked.
    view = navigate_to(appliance.collections.roles, 'Add')
    view.fill({'name_txt': '',
               'vm_restriction_select': 'Only User Owned'})
    assert view.add_button.disabled
    view.fill({'name_txt': 'test-required-name'})
    assert not view.add_button.disabled
    view.cancel_button.click()


@pytest.mark.tier(3)
def test_rolename_duplicate_validation(appliance):
    """
    Polarion:
        assignee: apagac
        casecomponent: Configuration
        initialEstimate: 1/8h
        tags: rbac
    """
    name = 'rol{}'.format(fauxfactory.gen_alphanumeric())
    role = appliance.collections.roles.create(name=name)
    assert role.exists
    view = navigate_to(appliance.collections.roles, 'Add')
    view.fill({'name_txt': name})
    view.add_button.click()
    view.flash.assert_message('Name has already been taken', 'error')
    view.cancel_button.click()


@pytest.mark.tier(3)
def test_delete_default_roles(appliance):
    """Test that CFME prevents a user from deleting a default role
    when selecting it from the Access Control EVM Role checklist

    Steps:
        * Login as Administrator user
        * Navigate to Configuration -> Role
        * Try editing the group EvmRole-approver

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = appliance.collections.roles.instantiate(name='EvmRole-approver')
    with pytest.raises(RBACOperationBlocked):
        role.delete()


@pytest.mark.tier(3)
def test_edit_default_roles(appliance):
    """Test that CFME prevents a user from editing a default role
    when selecting it from the Access Control EVM Role checklist

    Steps:
        * Login as Administrator user
        * Navigate to Configuration -> Role
        * Try editing the group EvmRole-auditor

    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = appliance.collections.roles.instantiate(name='EvmRole-auditor')
    newrole_name = "{}-{}".format(role.name, fauxfactory.gen_alphanumeric())
    role_updates = {'name': newrole_name}

    with pytest.raises(RBACOperationBlocked):
        role.update(role_updates)


@pytest.mark.tier(3)
def test_delete_roles_with_assigned_group(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = new_role(appliance)
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group_collection.create(description=group_description, role=role.name)

    with pytest.raises(RBACOperationBlocked):
        role.delete()


@pytest.mark.tier(3)
def test_assign_user_to_new_group(appliance, group_collection):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    role = new_role(appliance)  # call function to get role

    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection.create(description=group_description, role=role.name)

    new_user(appliance, [group])


def _test_vm_provision(appliance):
    logger.info("Checking for provision access")
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.toolbar.lifecycle.item_enabled('Provision VMs')

# this fixture is used in disabled tests. it should be updated along with tests
# def _test_vm_power_on():
#     """Ensures power button is shown for a VM"""
#     logger.info("Checking for power button")
#     vm_name = ## use collection.all and pick the first
#     logger.debug("VM " + vm_name + " selected")
#     if not vms.is_pwr_option_visible(vm_name, option=vms.InfraVm.POWER_ON):
#         raise OptionNotAvailable("Power button does not exist")


# Test using this method has been commented out
def _test_vm_removal(appliance, provider):
    logger.info("Testing for VM removal permission")
    vm = appliance.collections.infra_vms.all()[0]  # pick first vm from collection
    logger.debug("VM {} selected".format(vm.name))
    vm.delete(cancel=True)


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'product_features', [
        [['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'View'],
         ['Everything', 'Compute', 'Infrastructure', 'Virtual Machines', 'Accordions']]])
def test_permission_edit(appliance, request, product_features):
    """
    Ensures that changes in permissions are enforced on next login by attempting to navigate to
    a page with and without permissions to access that page

    Args:
        appliance: cfme appliance fixture
        request: pytest request fixture
        product_features: product features to set for test role
        action: reference to a function to execute under the test user context

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Configuration
        initialEstimate: 1h
        tags: rbac
    """
    role_name = fauxfactory.gen_alphanumeric()
    role = appliance.collections.roles.create(name=role_name,
                vm_restriction=None,
                product_features=[(['Everything'], False)] +  # role_features
                                 [(k, True) for k in product_features])
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection(appliance).create(description=group_description, role=role.name)
    user = new_user(appliance, [group])
    with user:
        # Navigation should succeed with valid permissions
        navigate_to(appliance.collections.infra_vms, 'VMsOnly')

    appliance.server.login_admin()
    role.update({'product_features': [(['Everything'], True)] +
                                     [(k, False) for k in product_features]
                 })
    with user:
        with pytest.raises(Exception, message='Permissions have not been updated'):
            navigate_to(appliance.collections.infra_vms, 'VMsOnly')

    @request.addfinalizer
    def _delete_user_group_role():
        for item in [user, group, role]:
            item.delete()


def _mk_role(appliance, name=None, vm_restriction=None, product_features=None):
    """Create a thunk that returns a Role object to be used for perm
       testing.  name=None will generate a random name

    """
    name = name or fauxfactory.gen_alphanumeric()
    return appliance.collections.roles.create(
        name=name,
        vm_restriction=vm_restriction,
        product_features=product_features
    )


def _go_to(cls_or_obj, dest='All'):
    """Create a thunk that navigates to the given destination"""
    def nav(appliance):
        if cls_or_obj == 'server':
            navigate_to(appliance.server, dest)
        else:
            navigate_to(cls_or_obj, dest)
    return nav


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'product_features,allowed_actions,disallowed_actions',
    [
        [  # Param Set 1
            [  # product_features
                [['Everything'], False],  # minimal permission
                [['Everything', 'Settings', 'Tasks'], True]
            ],
            {  # allowed_actions
                'tasks':
                    lambda appliance: appliance.browser.create_view(TasksView).tabs.default.click()
            },
            {  # disallowed actions
                'my services': _go_to(MyService),
                'chargeback': _go_to('server', 'Chargeback'),
                'clouds providers': _go_to(base_types()['cloud']),
                'infrastructure providers': _go_to(base_types()['infra']),
                'control explorer': _go_to('server', 'ControlExplorer'),
                'automate explorer': _go_to('server', 'AutomateExplorer')
            }
        ],
        [  # Param Set 2
            [  # product_features
                [['Everything'], True]  # full permissions
            ],
            {  # allowed_actions
                'my services': _go_to(MyService),
                'chargeback': _go_to('server', 'Chargeback'),
                'clouds providers': _go_to(base_types()['cloud']),
                'infrastructure providers': _go_to(base_types()['infra']),
                'control explorer': _go_to('server', 'ControlExplorer'),
                'automate explorer': _go_to('server', 'AutomateExplorer')
            },
            {}  # disallowed_actions
        ]
    ]
)
def test_permissions(appliance, product_features, allowed_actions, disallowed_actions):
    """ Test that that under the specified role the allowed acctions succeed
        and the disallowed actions fail

        Args:
            appliance: cfme_test appliance fixture
            role: reference to a function that will create a role object
            allowed_actions: Action(s) that should succeed under given roles
                             permission
            disallowed_actions: Action(s) that should fail under given roles
                                permission

        *_actions are a list of actions with each item consisting of a dictionary
            object: [ { "Action Name": function_reference_action }, ...]

    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Configuration
        initialEstimate: 1h
        tags: rbac
    """
    # create a user and role
    role = _mk_role(appliance, product_features=product_features)
    group_description = 'grp{}'.format(fauxfactory.gen_alphanumeric())
    group = group_collection(appliance).create(description=group_description, role=role.name)
    user = new_user(appliance, [group])
    fails = {}
    try:
        with user:
            navigate_to(appliance.server, 'LoggedIn')
            # TODO: split this test into 2 parameterized tests
            for name, action_thunk in sorted(allowed_actions.items()):
                try:
                    action_thunk(appliance)
                except Exception:
                    fails[name] = "{}: {}".format(name, traceback.format_exc())

            for name, action_thunk in sorted(disallowed_actions.items()):
                try:
                    with pytest.raises(Exception):
                        action_thunk(appliance)
                except pytest.fail.Exception:
                    fails[name] = "{}: {}".format(name, traceback.format_exc())

            if fails:
                message = ''
                for failure in fails.values():
                    message = "{}\n\n{}".format(message, failure)
                raise Exception(message)
    finally:
        appliance.server.login_admin()


def single_task_permission_test(appliance, product_features, actions):
    """Tests that action succeeds when product_features are enabled, and
       fail when everything but product_features are enabled"""
    # Enable only specified product features
    test_prod_features = [(['Everything'], False)] + [(f, True) for f in product_features]
    test_permissions(appliance, test_prod_features, actions, {})

    # Enable everything except product features
    test_prod_features = [(['Everything'], True)] + [(f, False) for f in product_features]
    test_permissions(appliance, test_prod_features, {}, actions)


@pytest.mark.tier(3)
def test_permissions_role_crud(appliance):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/5h
        casecomponent: Configuration
        tags: rbac
    """
    single_task_permission_test(appliance,
                                [['Everything', 'Settings', 'Configuration'],
                                 ['Everything', 'Services', 'Catalogs Explorer']],
                                {'Role CRUD': test_role_crud})


@pytest.mark.tier(3)
def test_permissions_vm_provisioning(appliance, provider):
    """
    Polarion:
        assignee: apagac
        caseimportance: medium
        casecomponent: Configuration
        initialEstimate: 1/5h
        tags: rbac
    """
    features = [
        ['Everything', 'Compute', 'Infrastructure', 'Virtual Machines', 'Accordions'],
        ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
         'Provision VMs']
    ]

    single_task_permission_test(
        appliance,
        features,
        {'Provision VM': _test_vm_provision}
    )


# This test is disabled until it has been rewritten
# def test_permissions_vm_power_on_access(appliance):
#    # Ensure VMs exist
#    if not vms.get_number_of_vms():
#        logger.debug("Setting up providers")
#        infra_provider
#        logger.debug("Providers setup")
#    single_task_permission_test(
#        appliance,
#        [
#            ['Infrastructure', 'Virtual Machines', 'Accordions'],
#            ['Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Operate', 'Power On']
#        ],
#        {'VM Power On': _test_vm_power_on}
#    )


# This test is disabled until it has been rewritten
# def test_permissions_vm_remove(appliance):
#    # Ensure VMs exist
#    if not vms.get_number_of_vms():
#        logger.debug("Setting up providers")
#        setup_infrastructure_providers()
#        logger.debug("Providers setup")
#    single_task_permission_test(
#        appliance,
#        [
#            ['Infrastructure', 'Virtual Machines', 'Accordions'],
#            ['Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Modify', 'Remove']
#        ],
#        {'Remove VM': _test_vm_removal}
#    )


@pytest.mark.tier(2)
def test_user_change_password(appliance, request):
    """
    Polarion:
        assignee: apagac
        initialEstimate: 1/8h
        casecomponent: Configuration
        tags: rbac
    """
    group_name = 'EvmGroup-user'
    group = group_collection(appliance).instantiate(description=group_name)

    user = new_user(appliance, [group])

    request.addfinalizer(user.delete)
    request.addfinalizer(appliance.server.login_admin)
    with user:
        appliance.server.logout()
        navigate_to(appliance.server, 'LoggedIn')
        assert appliance.server.current_full_name() == user.name
    appliance.server.login_admin()
    with update(user):
        user.credential = Credential(
            principal=user.credential.principal,
            secret="another_very_secret",
            verify_secret="another_very_secret",
        )
    with user:
        appliance.server.logout()
        navigate_to(appliance.server, 'LoggedIn')
        assert appliance.server.current_full_name() == user.name


def test_copied_user_password_inheritance(appliance, group_collection, request):
    """Test to verify that dialog for copied user should appear and password field should be
    empty

    Polarion:
        assignee: apagac
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/15h
    """
    group_name = 'EvmGroup-user'
    group = group_collection.instantiate(description=group_name)
    user = new_user(appliance, [group])
    request.addfinalizer(user.delete)
    view = navigate_to(user, 'Details')
    view.toolbar.configuration.item_select('Copy this User to a new User')
    view = user.create_view(AddUserView, wait='10s')
    assert view.password_txt.value == '' and view.password_verify_txt.value == ''
    view.cancel_button.click()


# Tenant/Project test cases
@test_requirements.multi_tenancy
def test_delete_default_tenant(appliance):
    """
    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: low
        tags: cfme_tenancy
        initialEstimate: 1/20h
        testSteps:
            1. Login as an 'Administrator' user
            2. Navigate to configuration > access control > tenants
            3. Select default tenant('My Company') from tenants table
            4. Delete using 'configuration > Delete selected items'
            5. Check whether default tenant is deleted or not
        expectedResults:
            1.
            2.
            3.
            4.
            5. Default tenant('My Company') must not be deleted
    """
    view = navigate_to(appliance.collections.tenants, "All")
    roottenant = appliance.collections.tenants.get_root_tenant()
    msg = 'Default Tenant "{}" can not be deleted'.format(roottenant.name)
    tenant = appliance.collections.tenants.instantiate(name=roottenant.name)
    appliance.collections.tenants.delete(tenant)
    assert view.flash.assert_message(msg)
    assert roottenant.exists


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
def test_superadmin_tenant_crud(request, appliance):
    """Test suppose to verify CRUD operations for CFME tenants

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: low
        tags: cfme_tenancy
        initialEstimate: 1/4h
        testSteps:
            1. Create tenant
            2. Update description of tenant
            3. Update name of tenant
            4. Delete tenant
    """
    tenant_collection = appliance.collections.tenants
    tenant = tenant_collection.create(
        name='tenant1{}'.format(fauxfactory.gen_alphanumeric()),
        description='tenant1 description',
        parent=tenant_collection.get_root_tenant()
    )

    @request.addfinalizer
    def _delete_tenant():
        if tenant.exists:
            tenant.delete()

    with update(tenant):
        tenant.description = "{}edited".format(tenant.description)
    with update(tenant):
        tenant.name = "{}edited".format(tenant.name)
    tenant.delete()


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
def test_superadmin_tenant_project_crud(request, appliance):
    """Test suppose to verify CRUD operations for CFME projects

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        testSteps:
            1. Create tenant
            2. Create project as child to tenant
            3. Update description of project
            4. Update name of project
            5. Delete project
            6. Delete tenant
    """
    tenant_collection = appliance.collections.tenants
    project_collection = appliance.collections.projects
    tenant = tenant_collection.create(
        name='tenant1{}'.format(fauxfactory.gen_alphanumeric()),
        description='tenant1 description',
        parent=tenant_collection.get_root_tenant())

    project = project_collection.create(
        name='project1{}'.format(fauxfactory.gen_alphanumeric()),
        description='project1 description',
        parent=project_collection.get_root_tenant())

    @request.addfinalizer
    def _delete_tenant_and_project():
        for item in [project, tenant]:
            if item.exists:
                item.delete()

    with update(project):
        project.description = "{}edited".format(project.description)
    with update(project):
        project.name = "{}_edited".format(project.name)
    project.delete()
    tenant.delete()


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
@pytest.mark.parametrize('number_of_childrens', [5])
def test_superadmin_child_tenant_crud(request, appliance, number_of_childrens):
    """Test CRUD operations for CFME child tenants, where several levels of tenants are created.

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1h
        testSteps:
            1. Create 5 tenants where the next tenant is always child to the previous one
            2. Update description of tenant(N-1)_* in the tree
            3. Update name of tenant(N-1)_*
            4. Delete all created tenants in reversed order
    """
    tenant_collection = appliance.collections.tenants
    tenant_list = []

    @request.addfinalizer
    def _delete_tenants():
        # reversed because we need to go from the last one
        for tenant in reversed(tenant_list):
            if tenant.exists:
                tenant.delete()

    tenant = tenant_collection.get_root_tenant()
    for i in range(1, number_of_childrens + 1):
        new_tenant = tenant_collection.create(
            name="tenant{}_{}".format(i, fauxfactory.gen_alpha(4)),
            description=fauxfactory.gen_alphanumeric(16),
            parent=tenant)
        tenant_list.append(new_tenant)
        tenant = new_tenant

    tenant_update = tenant.parent_tenant
    with update(tenant_update):
        tenant_update.description = "{}edited".format(tenant_update.description)
    with update(tenant_update):
        tenant_update.name = "{}edited".format(tenant_update.name)


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
@pytest.mark.parametrize('collection_name', ['tenants', 'projects'])
def test_unique_name_on_parent_level(request, appliance, collection_name):
    """Tenant or Project has always unique name on parent level. Same name cannot be used twice.

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/20h
        testSteps:
            1. Create tenant/project
            2. Create another tenant/project with the same name
            3. Creation will fail because object with the same name exists
            4. Delete created objects
    """
    object_collection = getattr(appliance.collections, collection_name)
    name_of_tenant = fauxfactory.gen_alphanumeric()
    tenant_description = 'description'

    tenant = object_collection.create(
        name=name_of_tenant,
        description=tenant_description,
        parent=object_collection.get_root_tenant())

    with pytest.raises(Exception,
                       match='Failed to add a new tenant resource - '
                             'Tenant: Name should be unique per parent'):
        tenant2 = object_collection.create(
            name=name_of_tenant,
            description=tenant_description,
            parent=object_collection.get_root_tenant())

    tenant.delete()

    tenant.delete_if_exists()
    try:
        tenant2.delete_if_exists()
    except NameError:
        pass


@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_superadmin_tenant_admin_crud(appliance, group_collection):
    """
    Super admin is able to create new tenant administrator

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Create new tenant admin user and assign him into group EvmGroup-tenant_administrator
            2. Update the user details and delete the user.
    """
    group_name = 'EvmGroup-tenant_administrator'
    group = group_collection.instantiate(description=group_name)
    user = new_user(appliance, [group])
    assert user.exists
    with update(user):
        user.name = "{}_edited".format(user.name)
    user.delete()
    assert not user.exists


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
def test_tenant_unique_catalog(appliance, request, catalog_obj):
    """
    Catalog name is unique per tenant. Every tenant can have catalog with
    name "catalog" defined.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.5
    """
    msg = "Name has already been taken"

    view = navigate_to(appliance.collections.catalogs, 'Add')
    view.fill({
        'name': catalog_obj.name,
        'description': catalog_obj.description
    })
    view.add_button.click()
    view.flash.wait_displayed(timeout=20)
    assert view.flash.read() == [msg]


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_service_template_catalogs_all_parents():
    """
    Members of child tenants can see service templates which are visible
    in parent tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_services_all_childs():
    """
    Members of parent tenant can see services of all child tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenant_osp_mapping_refresh():
    """
    There is new feature in 5.7, mapping of Openstack tenants to CFME
    tenants.

    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: Appliance
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.7
        testSteps:
            1. Switch "Tenant Mapping Enabled" checkbox to Yes when adding RHOS
            cloud provider
            2. Create new test tenant in RHOS
            3. Perform refresh of RHOS provider in CFME UI
            4. New tenants are created automatically

    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_providers_all_parents():
    """
    Child tenants can see providers which were defined in parent tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/6h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_miq_requests_all_childs():
    """
    Tenant members can see MIQ requests of this tenant and its children.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenant_osp_mapping_delete():
    """
    Tenants created by tenant mapping cannot be deleted.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.7
        testSteps:
            1. Add rhos which has at least one tenant enabled and perform refresh
            2. Navigate to Configuration -> Access Control -> tenants
            3. Try to delete any of the tenants created by tenant mapping process
            4. This is not possible until RHOS provider is removed from VMDB
            5. Try this again after provider is removed
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenant_ssui_users_can_see_their_services():
    """
    Self Service UI - users can see their services

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Configure LDAP authentication on CFME
            2. Create 2 different parent parent-tenants
                - marketing
                - finance
            3. Create groups marketing and finance (these are defined in LDAP) and
            group names in LDAP and CFME must match, assign these groups to corresponding
            tenants and assign them EvmRole-SuperAdministrator roles
            4. In LDAP we have 3 users:
                - bill -> member of marketing group
                - jim -> member of finance group
                - mike -> is member of both groups
            5. Add rhos/amazon providers and refresh them
                - BUG: if provider with the same IP is added to CFME already it is not
                seen in Cloud - Providers and it cannot be added again. Therefore you have
                to add 2 different providers as a workaround.
                - Providers must be added under corresponding tenants!!!
            6. Login as bill and create new catalog with  - finance_catalog and
            catalog item
                - catalog items cannot contain fields which requires input from users, known
                limitation based on information from Brad"s presentation, this is for froms
                that have dynamic dialogs items
            7. Login as jim and create new catalog with EC2 item
            8. Login as jim or bill, you should see catalog items of parent-tenants and for tenant
            they are in, mike user should see items from marketing or finance catalog based on which
            group is active in Classic UI
                - this does not work well - in SSUI - My Services and My requests does not show any
                items (correct) but number of services/requests is calculated also from services not
                relevant to actual tenant - this is fixed in next RC
    """
    pass


@pytest.mark.tier(3)
@test_requirements.multi_tenancy
def test_tenant_unique_automation_domain_name_on_parent_level(appliance, request):
    """
    Automation domain name is unique across parent tenants and cannot be
    used twice.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        caseposneg: negative
        initialEstimate: 1/2h
        startsin: 5.5
    """
    domain_name = fauxfactory.gen_alphanumeric()
    domain1 = appliance.collections.domains.create(name=domain_name, enabled=True)
    msg = "Name has already been taken"

    with pytest.raises(Exception, match=msg):
        domain2 = appliance.collections.domains.create(name=domain_name, enabled=True)

    domain1.delete()

    @request.addfinalizer
    def _delete_domain():
        if domain1.exists:
            domain1.delete()
        try:
            if domain2.exists:
                domain2.delete()
        except NameError:
            pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenantadmin_user_crud():
    """
    As a Tenant Admin I want to be able to create users in my tenant

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Login as super admin and create new tenant
            2. Create new role by copying EvmRole-tenant_administrator
            3. Create new group and choose role created in previous step and your
            tenant
            4. Create new tenant admin user and assign him into group created in
            previous step
            5. login as tenant admin
            6. Perform crud operations

            Note: BZ 1278484 - tenant admin role has no permissions to create new roles,
            Workaround is to add modify permissions to tenant_administrator role or Roles
            must be created by superadministrator. In 5.5.0.13 after giving additional permissions
            to tenant_admin,able to create new roles
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenant_automation_domains():
    """
    Tenants can see Automation domains owned by tenant or parent tenants

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Configure LDAP authentication on CFME
            2. Create 2 different parent parent-tenants
                - marketing
                - finance
            3. Create groups marketing and finance (these are defined in LDAP) and
            group names in LDAP and CFME must match, assign these groups to corresponding
            tenants and assign them EvmRole-SuperAdministrator roles
            4. In LDAP we have 3 users:
                - bill -> member of marketing group
                - jim -> member of finance group
                - mike -> is member of both groups
            5. In each tenant create new Automation domain and copy
            ManageIQ/System/Request/InspectMe instance and
            ManageIQ/System/Request/new_method method to new domain
            6. User can see only domains (locked) from his parent tenants and can
            create his own which are visible only to his tenant
    """
    pass


@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_superadmin_child_tenant_delete_parent_catalog(appliance, group_collection, request):
    """
    Child superadmin tenant should able to delete catalog belonging to
    superadmin in parent tenant. This is by design tenancy has not been
    split any further and at this point is not expected to be changed
    Note: As per below BZ#1375713,  Child superadmin tenant should not
    delete catalog belonging to superadmin in parent tenant. However as
    per the current code base this is by design: "ServiceTemplate"
    => :ancestor_ids,
    https://github.com/ManageIQ/manageiq/blob/2a66cb59e26816c7296896620b5b
    7731b350943d/lib/rbac/filterer.rb#L114
    You"re able to see Catalog items of parent and ancestor tenants.  If
    your role has permission to modify catalog items / delete them, and
    you can to see ones from ancestor tenants, then you can delete them.

    Bugzilla:
        1375713

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/2h
        startsin: 5.5
    """
    tenant_collection = appliance.collections.tenants
    root_tenant = tenant_collection.get_root_tenant()
    catalog_name = fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    new_tenant = tenant_collection.create(
        name="tenant{}".format(fauxfactory.gen_alpha(4)),
        description=fauxfactory.gen_alphanumeric(16),
        parent=root_tenant)

    group = group_collection.create(description='grp{}'.format(fauxfactory.gen_alphanumeric()),
                                    role="EvmRole-super_administrator",
                                    tenant="{}/{}".format(root_tenant.name, new_tenant.name))
    user = new_user(appliance, [group])

    @request.addfinalizer
    def _delete_user_group_tenant():
        for item in [user, group, new_tenant]:
            if item.exists:
                item.delete()

    try:
        with user:
            navigate_to(appliance.server, 'LoggedIn')
            cat.delete()
            assert not cat.exists
    finally:
        user.appliance.server.login_admin()


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(1)
@test_requirements.multi_tenancy
def test_verify_groups_for_tenant_user():
    """
    verify if only 1 group displayed when login as tenant user ()that one
    where user belongs to)

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_service_template_items_all_parents():
    """
    Child tenants can see all service template items defined in parent
    tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/2h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenantadmin_group_crud():
    """
    As a Tenant Admin I want to be able to create groups related to the
    roles in my tenant and assign roles

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Login as tenant admin
            2. Navigate to Configure - Configuration - Access Control - Groups
            3. Configuration - Add a new group
            4. Assign Group name, role and Project/tenant and click Add
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_vms_all_childs():
    """
    Members of parent tenant can see all VMs/instances created by users in
    child tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@test_requirements.multi_tenancy
def test_tenant_ldap_group_switch_between_tenants():
    """
    User who is member of 2 or more LDAP groups can switch between tenants

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: high
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
        testSteps:
            1. Configure LDAP authentication on CFME
            2. Create 2 different parent parent-tenants
                - marketing
                - finance
            3. Create groups marketing and finance (these are defined in LDAP) and
            group names in LDAP and CFME must match, assign these groups to corresponding
            tenants and assign them EvmRole-SuperAdministrator roles
            4. In LDAP we have 3 users:
                - bill -> member of marketing group
                - jim -> member of finance group
                - mike -> is member of both groups
            5. Login as mike user who is member of 2 different tenants
            6. User is able switch between groups - switching is done in a way
            that current current group which is chosen is writtent into DB as
            active group. Therefore user who is assigned to more groups must login
            to Classic UI and switch to desired group. Afterthat he is able login
            via Self Service UI to desired tenant

    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream("upstream")
@pytest.mark.tier(2)
@test_requirements.multi_tenancy
def test_tenant_visibility_miq_ae_namespaces_all_parents():
    """
    Child tenants can see MIQ AE namespaces of parent tenants.

    Polarion:
        assignee: nachandr
        casecomponent: Configuration
        caseimportance: medium
        tags: cfme_tenancy
        initialEstimate: 1/4h
        startsin: 5.5
    """
    pass


@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@test_requirements.rbac
@pytest.mark.tier(2)
def test_tags_manual_features():
    """
    Test that user can edit tags of an VM when he has role created by disabling 'Everything'
    and then enabling every other checkbox.

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: high
        initialEstimate: 1/5h
        startsin: 5.11
        setup:
            1. Have an infra provider added and testvm created
        testSteps:
            1. Create new role. Disable 'Everything' and then manually enable each check box
                except 'Everything'.
            2. Create new group based on this role; Create new user as a member of this group
            3. Login as newly created user
            4. Navigate to testing vm and try to Policy -> Edit Tags
        expectedResults:
            1. New role created
            2. New group created; New user created
            3. Login successful
            4. Edit Tags screen displayed; no error in evm.log
    Bugzilla:
        1684472
    """
    pass


@pytest.mark.manual
@pytest.mark.provider([OpenshiftProvider], override=True)
@test_requirements.rbac
@pytest.mark.tier(2)
def test_host_clusters_pod_filter():
    """
    Test that user with Hosts & Clusters filter is able to see pods belonging to that filter only

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: high
        initialEstimate: 1/4h
        startsin: 5.10.3
        setup:
            1. Have at least two OCP providers added with some pods
        testSteps:
            1. Create new role with Everything -> Compute enabled only
            2. Create new group based on this role and in Hosts & Clusters tab check one of the
                OCP providers
            3. Create an user as a member of this group
            4. Login as the new user and navigate to Compute -> Containers -> Providers
            5. Navigate to Compute -> Containers -> Pods
        expectedResults:
            1. Role created
            2. Group created
            3. User created
            4. Only one OCP provider displayed; this is the one checked in Hosts & Clusters
            5. Only pods from one OCP provider are displayed
    Bugzilla:
        1631694
    """
    pass


@pytest.mark.manual
@test_requirements.rbac
@pytest.mark.tier(2)
def test_my_tasks_api():
    """
    Test that user with My Tasks product feature can see only his tasks via API

    Polarion:
        assignee: apagac
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/6h
        startsin: 5.10
        testSteps:
            1. Create a user with Settings -> Tasks -> View -> My Tasks (but not All Tasks),
                for example EvmRole-support
            2. Navigate to Tasks via UI, verify you can see only "My Tasks"
            3. Query API with the user: curl -k "https://<username>:<password>@<IP>/api/tasks/"
        expectedResults:
            1. User created
            2. "My Tasks" displayed
            3. Only tasks belonging to the user displayed
    Bugzilla:
        1639387
    """
    pass
