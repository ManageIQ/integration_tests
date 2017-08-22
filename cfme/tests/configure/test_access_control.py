# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import traceback

from cfme.configure.access_control import User, Group, Role, Tenant, Project
from utils import error
import cfme.fixtures.pytest_selenium as sel
from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.automate.explorer import AutomateExplorer  # NOQA
from cfme.base import Server
from cfme.control.explorer import ControlExplorer  # NOQA
from cfme.exceptions import OptionNotAvailable
from cfme.common.provider import base_types
from cfme.infrastructure import virtual_machines as vms
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.myservice import MyService
from cfme.web_ui import flash, Table, InfoBlock, toolbar as tb
from cfme.configure import tasks
from fixtures.provider import setup_one_or_skip
from utils.appliance.implementations.ui import navigate_to
from utils.blockers import BZ
from utils.log import logger
from utils.providers import ProviderFilter
from utils.update import update
from utils import version


records_table = Table("//div[@id='main_div']//table")
usergrp = Group(description='EvmGroup-user')
group_table = Table("//div[@id='main_div']//table")


pytestmark = test_requirements.rbac


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[VMwareProvider])
    return setup_one_or_skip(request, filters=[prov_filter])


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


def new_user(group=usergrp):
    return User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group,
        cost_center='Workload',
        value_assign='Database')


def new_group(role='EvmRole-approver'):
    return Group(
        description='grp' + fauxfactory.gen_alphanumeric(),
        role=role)


def new_role():
    return Role(
        name='rol' + fauxfactory.gen_alphanumeric(),
        vm_restriction='None')


def get_tag():
    return InfoBlock('Smart Management', 'My Company Tags').text


@pytest.fixture(scope='function')
def check_item_visibility(tag):
    def _check_item_visibility(item, user_restricted):
        category_name = ' '.join((tag.category.display_name, '*'))
        item.edit_tags(category_name, tag.display_name)
        with user_restricted:
            assert item.exists
        item.remove_tag(category_name, tag.display_name)
        with user_restricted:
            assert not item.exists
    return _check_item_visibility


# User test cases
@pytest.mark.tier(2)
def test_user_crud():
    user = new_user()
    user.create()
    with update(user):
        user.name = user.name + "edited"
    copied_user = user.copy()
    copied_user.delete()
    user.delete()


# @pytest.mark.meta(blockers=[1035399]) # work around instead of skip
@pytest.mark.tier(2)
def test_user_login():
    user = new_user()
    user.create()
    try:
        with user:
            navigate_to(Server, 'Dashboard')
    finally:
        user.appliance.server.login_admin()


@pytest.mark.tier(3)
def test_user_duplicate_name(appliance):
    region = appliance.server_region
    nu = new_user()
    nu.create()
    msg = version.pick({
        version.LOWEST: "Userid has already been taken",
        '5.8': "Userid is not unique within region {}".format(region)
    })
    with error.expected(msg):
        nu.create()


group_user = Group("EvmGroup-user")


@pytest.mark.tier(3)
def test_username_required_error_validation():
    user = User(
        name="",
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Name can't be blank"):
        user.create()


@pytest.mark.tier(3)
def test_userid_required_error_validation():
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=Credential(principal='', secret='redhat'),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Userid can't be blank"):
        user.create()


@pytest.mark.tier(3)
def test_user_password_required_error_validation():
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret=None),
        email='xyz@redhat.com',
        group=group_user)
    if version.current_version() < "5.5":
        check = "Password_digest can't be blank"
    else:
        check = "Password can't be blank"
    with error.expected(check):
        user.create()


@pytest.mark.tier(3)
def test_user_group_error_validation():
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group='')
    with error.expected("A User must be assigned to a Group"):
        user.create()


@pytest.mark.tier(3)
def test_user_email_error_validation():
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyzdhat.com',
        group=group_user)
    with error.expected("Email must be a valid email address"):
        user.create()


@pytest.mark.tier(2)
def test_user_edit_tag():
    user = new_user()
    user.create()
    user.edit_tags("Cost Center *", "Cost Center 001")
    assert get_tag() == "Cost Center: Cost Center 001", "User edit tag failed"
    user.delete()


@pytest.mark.tier(3)
def test_user_remove_tag():
    user = new_user()
    user.create()
    user.edit_tags("Department", "Engineering")
    user.remove_tag("Department", "Engineering")
    navigate_to(user, 'Details')
    assert get_tag() != "Department: Engineering", "Remove User tag failed"
    user.delete()


@pytest.mark.tier(3)
def test_delete_default_user():
    """Test for deleting default user Administrator.

    Steps:
        * Login as Administrator user
        * Try deleting the user
    """
    user = User(name='Administrator')
    navigate_to(User, 'All')
    row = records_table.find_row_by_cells({'Full Name': user.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Delete selected Users', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match('Default EVM User "{}" cannot be deleted' .format(user.name))


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[BZ(1090877)])
@pytest.mark.meta(blockers=[BZ(1408479)], forced_streams=["5.7", "upstream"])
@pytest.mark.uncollectif(lambda: version.current_version() >= "5.7")
def test_current_user_login_delete(request):
    """Test for deleting current user login.

    Steps:
        * Login as Admin user
        * Create a new user
        * Login with the new user
        * Try deleting the user
    """
    group_user = Group("EvmGroup-super_administrator")
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group_user)
    user.create()
    request.addfinalizer(user.delete)
    request.addfinalizer(user.appliance.server.login_admin())
    with user:
        if version.current_version() >= '5.7':
            navigate_to(user, 'Details')
            menu_item = ('Configuration', 'Delete this User')
            assert tb.exists(*menu_item) and tb.is_greyed(*menu_item), "Delete User is not dimmed"
        else:
            with error.expected("Current EVM User \"{}\" cannot be deleted".format(user.name)):
                user.delete()


@pytest.mark.tier(3)
def test_tagvis_user(user_restricted, check_item_visibility):
    """ Tests if group honour tag visibility feature
    Prerequirement:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to group
        2. Login as restricted user, group is visible for user
        3. As admin remove tag from group
        4. Login as restricted user, group is not visible for user
    """
    check_item_visibility(user_restricted, user_restricted)


@pytest.mark.tier(2)
# Group test cases
def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
    group.delete()


@pytest.mark.tier(2)
def test_group_crud_with_tag(a_provider, category, tag):
    """Test for verifying group create with tag defined

    Steps:
        * Login as Admin user
        * Navigate to add group page
        * Fill all fields
        * Set tag
        * Save group
    """
    group = Group(
        description='grp{}'.format(fauxfactory.gen_alphanumeric()),
        role='EvmRole-approver',
        tag=[category.display_name, tag.display_name],
        host_cluster=[a_provider.data['name']],
        vm_template=[a_provider.data['name'], a_provider.data['datacenters'][0],
                     'Discovered virtual machine']
    )
    group.create()
    with update(group):
        group.tag = [tag.category.display_name, tag.display_name]
        group.host_cluster = [a_provider.data['name']]
        group.vm_template = [a_provider.data['name'], a_provider.data['datacenters'][0],
                             'Discovered virtual machine']
    group.delete()


@pytest.mark.tier(3)
def test_group_duplicate_name(appliance):
    region = appliance.server_region
    group = new_group()
    group.create()
    msg = version.pick({
        version.LOWEST: "Description has already been taken",
        '5.8': "Description is not unique within region {}".format(region)
    })
    with error.expected(msg):
        group.create()


@pytest.mark.tier(2)
def test_group_edit_tag():
    group = new_group()
    group.create()
    group.edit_tags("Cost Center *", "Cost Center 001")
    assert get_tag() == "Cost Center: Cost Center 001", "Group edit tag failed"
    group.delete()


@pytest.mark.tier(2)
def test_group_remove_tag():
    group = new_group()
    group.create()
    navigate_to(group, 'Edit')
    group.edit_tags("Department", "Engineering")
    group.remove_tag("Department", "Engineering")
    assert get_tag() != "Department: Engineering", "Remove Group tag failed"
    group.delete()


@pytest.mark.tier(3)
def test_group_description_required_error_validation():
    error_text = "Description can't be blank"
    group = Group(description=None, role='EvmRole-approver')
    with error.expected(error_text):
        group.create()
    flash.dismiss()


@pytest.mark.tier(3)
def test_delete_default_group():
    flash_msg = "EVM Group \"{}\": Error during delete: A read only group cannot be deleted."
    group = Group(description='EvmGroup-administrator')
    view = navigate_to(Group, 'All')
    row = group_table.find_row_by_cells({'Name': group.description})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    view.configuration.item_select('Delete selected Groups', handle_alert=True)
    view.flash.assert_message(flash_msg.format(group.description))


@pytest.mark.tier(3)
def test_delete_group_with_assigned_user():
    flash_msg = version.pick({
        '5.6': ("EVM Group \"{}\": Error during delete: Still has users assigned"),
        '5.5': ("EVM Group \"{}\": Error during \'destroy\': Still has users assigned")})
    group = new_group()
    group.create()
    user = new_user(group=group)
    user.create()
    with error.expected(flash_msg.format(group.description)):
        group.delete()


@pytest.mark.tier(3)
def test_edit_default_group():
    flash_msg = 'Read Only EVM Group "{}" can not be edited'
    group = Group(description='EvmGroup-approver')
    navigate_to(Group, 'All')
    row = group_table.find_row_by_cells({'Name': group.description})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Edit the selected Group')
    flash.assert_message_match(flash_msg.format(group.description))


@pytest.mark.tier(3)
def test_edit_sequence_usergroups(request):
    """Test for editing the sequence of user groups for LDAP lookup.

    Steps:
        * Login as Administrator user
        * create a new group
        * Edit the sequence of the new group
        * Verify the changed sequence
    """
    group = new_group()
    group.create()
    request.addfinalizer(group.delete)
    view = navigate_to(Group, 'All')
    row = view.table.row(name=group.description)
    original_sequence = row.sequence.text
    group.set_group_order(group.description)
    row = view.table.row(name=group.description)
    changed_sequence = row.sequence.text
    assert original_sequence != changed_sequence, "Edit Sequence Failed"


@pytest.mark.tier(3)
def test_tagvis_group(user_restricted, group_with_tag, check_item_visibility):
    """ Tests if group honour tag visibility feature
    Prerequirement:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to group
        2. Login as restricted user, group is visible for user
        3. As admin remove tag from group
        4. Login as restricted user, group is not visible for user
    """
    check_item_visibility(group_with_tag, user_restricted)


# Role test cases
@pytest.mark.tier(2)
def test_role_crud():
    role = new_role()
    role.create()
    with update(role):
        role.name = role.name + "edited"
    copied_role = role.copy()
    copied_role.delete()
    role.delete()


@pytest.mark.tier(3)
def test_rolename_required_error_validation():
    role = Role(
        name=None,
        vm_restriction='Only User Owned')
    with error.expected("Name can't be blank"):
        role.create()


@pytest.mark.tier(3)
def test_rolename_duplicate_validation():
    role = new_role()
    role.create()
    with error.expected("Name has already been taken"):
        role.create()


@pytest.mark.tier(3)
def test_delete_default_roles():
    flash_msg = version.pick({
        '5.6': ("Role \"{}\": Error during delete: Cannot delete record "
                "because of dependent entitlements"),
        '5.5': ("Role \"{}\": Error during \'destroy\': Cannot delete record "
                "because of dependent miq_groups")})
    role = Role(name='EvmRole-approver')
    with error.expected(flash_msg.format(role.name)):
        role.delete()


@pytest.mark.tier(3)
def test_edit_default_roles():
    role = Role(name='EvmRole-auditor')
    navigate_to(role, 'Edit')
    flash.assert_message_match("Read Only Role \"{}\" can not be edited" .format(role.name))


@pytest.mark.tier(3)
def test_delete_roles_with_assigned_group():
    flash_msg = version.pick({
        '5.6': ("Role \"{}\": Error during delete: Cannot delete record "
                "because of dependent entitlements"),
        '5.5': ("Role \"{}\": Error during \'destroy\': Cannot delete record "
                "because of dependent miq_groups")})
    role = new_role()
    role.create()
    group = new_group(role=role.name)
    group.create()
    with error.expected(flash_msg.format(role.name)):
        role.delete()


@pytest.mark.tier(3)
def test_assign_user_to_new_group():
    role = new_role()  # call function to get role
    role.create()
    group = new_group(role=role.name)
    group.create()
    user = new_user(group=group)
    user.create()


def _test_vm_provision():
    logger.info("Checking for provision access")
    navigate_to(vms.Vm, 'VMsOnly')
    vms.lcl_btn("Provision VMs")


def _test_vm_power_on():
    """Ensures power button is shown for a VM"""
    logger.info("Checking for power button")
    vm_name = vms.Vm.get_first_vm_title()
    logger.debug("VM " + vm_name + " selected")
    if not vms.is_pwr_option_visible(vm_name, option=vms.Vm.POWER_ON):
        raise OptionNotAvailable("Power button does not exist")


def _test_vm_removal():
    logger.info("Testing for VM removal permission")
    vm_name = vms.get_first_vm()
    logger.debug("VM " + vm_name + " selected")
    vms.remove(vm_name, cancel=True)


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'product_features, action',
    [(
        {version.LOWEST: [['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
             'Provision VMs']],
         '5.6': [['Everything', 'Compute', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
             'Provision VMs']]},
        _test_vm_provision)])
def test_permission_edit(appliance, request, product_features, action):
    """
    Ensures that changes in permissions are enforced on next login
    """
    product_features = version.pick(product_features)
    request.addfinalizer(appliance.server.login_admin())
    role_name = fauxfactory.gen_alphanumeric()
    role = Role(name=role_name,
                vm_restriction=None,
                product_features=[(['Everything'], False)] +  # role_features
                                 [(k, True) for k in product_features])
    role.create()
    group = new_group(role=role.name)
    group.create()
    user = new_user(group=group)
    user.create()
    with user:
        try:
            action()
        except Exception:
            pytest.fail('Incorrect permissions set')
    appliance.server.login_admin()
    role.update({'product_features': [(['Everything'], True)] +
                                     [(k, False) for k in product_features]
                 })
    with user:
        try:
            with error.expected(Exception):
                action()
        except error.UnexpectedSuccessException:
            pytest.Fails('Permissions have not been updated')


def _mk_role(name=None, vm_restriction=None, product_features=None):
    """Create a thunk that returns a Role object to be used for perm
       testing.  name=None will generate a random name

    """
    name = name or fauxfactory.gen_alphanumeric()
    return lambda: Role(name=name,
                        vm_restriction=vm_restriction,
                        product_features=product_features)


def _go_to(cls, dest='All'):
    """Create a thunk that navigates to the given destination"""
    return lambda: navigate_to(cls, dest)


cat_name = "Settings"


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'role,allowed_actions,disallowed_actions',
    [[_mk_role(product_features=[[['Everything'], False],  # minimal permission
                                 [['Everything', cat_name, 'Tasks'], True]]),
      {'tasks': lambda: sel.click(tasks.buttons.default)},  # can only access one thing
      {
          'my services': _go_to(MyService),
          'chargeback': _go_to(Server, 'Chargeback'),
          'clouds providers': _go_to(base_types()['cloud']),
          'infrastructure providers': _go_to(base_types()['infra']),
          'control explorer': _go_to(Server, 'ControlExplorer'),
          'automate explorer': _go_to(Server, 'AutomateExplorer')}],
     [_mk_role(product_features=[[['Everything'], True]]),  # full permissions
      {
          'my services': _go_to(MyService),
          'chargeback': _go_to(Server, 'Chargeback'),
          'clouds providers': _go_to(base_types()['cloud']),
          'infrastructure providers': _go_to(base_types()['infra']),
          'control explorer': _go_to(Server, 'ControlExplorer'),
          'automate explorer': _go_to(Server, 'AutomateExplorer')},
      {}]])
@pytest.mark.meta(blockers=[1262759])
def test_permissions(appliance, role, allowed_actions, disallowed_actions):
    # create a user and role
    role = role()  # call function to get role
    role.create()
    group = new_group(role=role.name)
    group.create()
    user = new_user(group=group)
    user.create()
    fails = {}
    try:
        with user:
            appliance.server.login_admin()
            for name, action_thunk in allowed_actions.items():
                try:
                    action_thunk()
                except Exception:
                    fails[name] = "{}: {}".format(name, traceback.format_exc())
            for name, action_thunk in disallowed_actions.items():
                try:
                    with error.expected(Exception):
                        action_thunk()
                except error.UnexpectedSuccessException:
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
    test_permissions(appliance, _mk_role(name=fauxfactory.gen_alphanumeric(),
                              product_features=[(['Everything'], False)] +
                              [(f, True) for f in product_features]),
                     actions,
                     {})
    test_permissions(appliance, _mk_role(name=fauxfactory.gen_alphanumeric(),
                              product_features=[(['Everything'], True)] +
                              [(f, False) for f in product_features]),
                     {},
                     actions)


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1262764])
def test_permissions_role_crud(appliance):
    single_task_permission_test(appliance,
                                [['Everything', cat_name, 'Configuration'],
                                 ['Everything', 'Services', 'Catalogs Explorer']],
                                {'Role CRUD': test_role_crud})


@pytest.mark.tier(3)
def test_permissions_vm_provisioning(appliance):
    features = version.pick({
        version.LOWEST: [
            ['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
                'Provision VMs']
        ],
        '5.6': [
            ['Everything', 'Compute', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
                'Provision VMs']
        ]})
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


# commenting this out, there is validation around the 'no group selected'and we have a test for it
# @pytest.mark.meta(blockers=[1154112])
# def test_user_add_button_should_be_disabled_without_group(soft_assert):
#     from cfme.web_ui import fill, form_buttons
#     navigate_to(User, 'Add')
#     pw = fauxfactory.gen_alphanumeric()
#     fill(User.user_form, {
#         "name_txt": fauxfactory.gen_alphanumeric(),
#         "userid_txt": fauxfactory.gen_alphanumeric(),
#         "password_txt": pw,
#         "password_verify_txt": pw,
#         "email_txt": "test@test.test"
#     })
#     assert not sel.is_displayed(form_buttons.add), "The Add button should not be displayed!"


@pytest.mark.tier(2)
def test_user_change_password(appliance, request):
    user = User(
        name="user {}".format(fauxfactory.gen_alphanumeric()),
        credential=Credential(
            principal="user_principal_{}".format(fauxfactory.gen_alphanumeric()),
            secret="very_secret",
            verify_secret="very_secret"
        ),
        email="test@test.test",
        group=usergrp,
    )
    user.create()
    request.addfinalizer(user.delete)
    request.addfinalizer(appliance.server.login_admin())
    with user:
        appliance.server.logout()
        appliance.server.login(user)
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
        appliance.server.login(user)
        assert appliance.server.current_full_name() == user.name


# Tenant/Project test cases
@pytest.mark.tier(3)
def test_superadmin_tenant_crud(request):
    """Test suppose to verify CRUD operations for CFME tenants

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Steps:
        * Create tenant
        * Update description of tenant
        * Update name of tenat
        * Delete tenant
    """
    tenant = Tenant(
        name='tenant1' + fauxfactory.gen_alphanumeric(),
        description='tenant1 description')

    @request.addfinalizer
    def _delete_tenant():
        if tenant.exists:
            tenant.delete()

    tenant.create()
    with update(tenant):
        tenant.description = tenant.description + "edited"
    with update(tenant):
        tenant.name = tenant.name + "edited"
    tenant.delete()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1387088, forced_streams=['5.7', 'upstream'])])
def test_superadmin_tenant_project_crud(request):
    """Test suppose to verify CRUD operations for CFME projects

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Steps:
        * Create tenant
        * Create project as child to tenant
        * Update description of project
        * Update name of project
        * Delete project
        * Delete tenant
    """
    tenant = Tenant(
        name='tenant1' + fauxfactory.gen_alphanumeric(),
        description='tenant1 description')
    project = Project(
        name='project1' + fauxfactory.gen_alphanumeric(),
        description='project1 description',
        parent_tenant=tenant)

    @request.addfinalizer
    def _delete_tenant_and_project():
        for item in [project, tenant]:
            if item.exists:
                item.delete()

    tenant.create()
    project.create()
    with update(project):
        project.description = project.description + "edited"
    with update(project):
        project.name = project.name + "edited"
    project.delete()
    tenant.delete()


@pytest.mark.tier(3)
@pytest.mark.parametrize('number_of_childrens', [5])
def test_superadmin_child_tenant_crud(request, number_of_childrens):
    """Test CRUD operations for CFME child tenants, where several levels of tenants are created.

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Steps:
        * Create 5 tenants where the next tenant is always child to the previous one
        * Update description of tenant(N-1)_* in the tree
        * Update name of tenant(N-1)_*
        * Delete all created tenants in reversed order
    """

    tenant = None
    tenant_list = []

    @request.addfinalizer
    def _delete_tenants():
        # reversed because we need to go from the last one
        for tenant in reversed(tenant_list):
            if tenant.exists:
                tenant.delete()

    for i in range(1, number_of_childrens + 1):
        new_tenant = Tenant(
            name="tenant{}_{}".format(i, fauxfactory.gen_alpha(4)),
            description=fauxfactory.gen_alphanumeric(16),
            parent_tenant=tenant)
        tenant_list.append(new_tenant)
        new_tenant.create()
        tenant = new_tenant

    tenant_update = tenant.parent_tenant
    with update(tenant_update):
        tenant_update.description = tenant_update.description + "edited"
    with update(tenant_update):
        tenant_update.name = tenant_update.name + "edited"

    for tenant_item in reversed(tenant_list):
        tenant_item.delete()
        assert not tenant_item.exists


@pytest.mark.tier(3)
@pytest.mark.parametrize("object_type", [Tenant, Project])
def test_tenant_unique_tenant_project_name_on_parent_level(request, object_type):
    """Tenant or Project has always unique name on parent level. Same name cannot be used twice.

    Prerequisities:
        * This test is not depending on any other test and can be executed against fresh appliance.

    Steps:
        * Create tenant or project
        * Create another tenant or project with the same name
        * Creation will fail because object with the same name exists
        * Delete created objects
    """

    name_of_tenant = object_type.__name__ + fauxfactory.gen_alphanumeric()
    tenant_description = object_type.__name__ + 'description'

    tenant = object_type(
        name=name_of_tenant,
        description=tenant_description)

    tenant2 = object_type(
        name=name_of_tenant,
        description=tenant_description)

    @request.addfinalizer
    def _delete_tenant():
        if tenant.exists:
            tenant.delete()
        if tenant2.exists:
            tenant2.delete()

    tenant.create()
    with error.expected("Validation failed: Name should be unique per parent"):
        tenant2.create()
    tenant.delete()
