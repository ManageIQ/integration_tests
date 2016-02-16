# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import traceback
import cfme.configure.access_control as ac
import utils.error as error
import cfme.fixtures.pytest_selenium as sel
from cfme import Credential
from cfme import login
from cfme.configure.access_control import set_group_order
from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure import virtual_machines
from cfme.web_ui import flash, Table, InfoBlock, toolbar as tb
from cfme.web_ui.menu import nav
from cfme.configure import tasks
from utils.blockers import BZ
from utils.log import logger
from utils.providers import setup_a_provider
from utils.update import update
from utils import version

records_table = Table("//div[@id='main_div']//table")
usergrp = ac.Group(description='EvmGroup-user')
group_table = Table("//div[@id='main_div']//table")


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider(validate=True, check_existing=True)

# due to pytest.mark.meta(blockers=[1035399]), non admin users can't login
# with no providers added
pytestmark = [pytest.mark.usefixtures("setup_first_provider")]


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


def new_user(group=usergrp):
    return ac.User(name='user' + fauxfactory.gen_alphanumeric(),
                   credential=new_credential(),
                   email='xyz@redhat.com',
                   group=group,
                   cost_center='Workload',
                   value_assign='Database')


def new_group(role='EvmRole-approver'):
    return ac.Group(description='grp' + fauxfactory.gen_alphanumeric(),
                    role=role)


def new_role():
    return ac.Role(name='rol' + fauxfactory.gen_alphanumeric(),
                   vm_restriction='None')


def get_tag():
    return InfoBlock('Smart Management', 'My Company Tags').text


# User test cases
def test_user_crud():
    user = new_user()
    user.create()
    with update(user):
        user.name = user.name + "edited"
    copied_user = user.copy()
    copied_user.delete()
    user.delete()


# @pytest.mark.meta(blockers=[1035399]) # work around instead of skip
def test_user_login():
    user = new_user()
    user.create()
    try:
        with user:
            sel.force_navigate('dashboard')
    finally:
        login.login_admin()


def test_user_duplicate_name():
    nu = new_user()
    nu.create()
    with error.expected("Userid has already been taken"):
        nu.create()

group_user = ac.Group("EvmGroup-user")


def test_username_required_error_validation():
    user = ac.User(
        name=None,
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Name can't be blank"):
        user.create()


def test_userid_required_error_validation():
    user = ac.User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=Credential(principal=None, secret='redhat'),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Userid can't be blank"):
        user.create()


def test_user_password_required_error_validation():
    user = ac.User(
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


@pytest.mark.meta(
    blockers=[
        BZ(1118040, unblock=lambda appliance_version: appliance_version < "5.3")
    ]
)
def test_user_group_error_validation():
    user = ac.User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=None)
    with error.expected("A User must be assigned to a Group"):
        user.create()


def test_user_email_error_validation():
    user = ac.User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyzdhat.com',
        group=group_user)
    with error.expected("Email must be a valid email address"):
        user.create()


def test_user_edit_tag():
    user = new_user()
    user.create()
    user.edit_tags("Cost Center *", "Cost Center 001")
    assert get_tag() == "Cost Center: Cost Center 001", "User edit tag failed"
    user.delete()


def test_user_remove_tag():
    user = new_user()
    user.create()
    user.edit_tags("Department", "Engineering")
    user.remove_tag("Department", "Engineering")
    sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": user})
    assert get_tag() != "Department: Engineering", "Remove User tag failed"
    user.delete()


def test_delete_default_user():
    """Test for deleting default user Administrator.

    Steps:
        * Login as Administrator user
        * Try deleting the user
    """
    user = ac.User(name='Administrator')
    sel.force_navigate("cfg_accesscontrol_users")
    column = version.pick({version.LOWEST: "Name",
        "5.4": "Full Name"})
    row = records_table.find_row_by_cells({column: user.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Delete selected Users', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match('Default EVM User "{}" cannot be deleted' .format(user.name))


@pytest.mark.meta(automates=[1090877])
def test_current_user_login_delete(request):
    """Test for deleting current user login.

    Steps:
        * Login as Admin user
        * Create a new user
        * Login with the new user
        * Try deleting the user
    """
    group_user = ac.Group("EvmGroup-super_administrator")
    user = ac.User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group_user)
    user.create()
    request.addfinalizer(user.delete)
    request.addfinalizer(login.login_admin)
    with user:
        with error.expected("Current EVM User \"%s\" cannot be deleted" % user.name):
            user.delete()


# Group test cases
def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
    group.delete()


def test_group_duplicate_name():
    group = new_group()
    group.create()
    with error.expected("Description has already been taken"):
        group.create()


def test_group_edit_tag():
    group = new_group()
    group.create()
    group.edit_tags("Cost Center *", "Cost Center 001")
    assert get_tag() == "Cost Center: Cost Center 001", "Group edit tag failed"
    group.delete()


def test_group_remove_tag():
    group = new_group()
    group.create()
    sel.force_navigate("cfg_accesscontrol_group_ed", context={"group": group})
    group.edit_tags("Department", "Engineering")
    group.remove_tag("Department", "Engineering")
    assert get_tag() != "Department: Engineering", "Remove Group tag failed"
    group.delete()


def test_description_required_error_validation():
    group = ac.Group(description=None, role='EvmRole-approver')
    with error.expected("Description can't be blank"):
        group.create()


def test_delete_default_group():
    flash_msg = \
        'EVM Group "{}": Error during \'destroy\': A read only group cannot be deleted.'
    group = ac.Group(description='EvmGroup-administrator')
    sel.force_navigate("cfg_accesscontrol_groups")
    row = group_table.find_row_by_cells({'Name': group.description})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Delete selected Groups', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match(flash_msg.format(group.description))


def test_delete_group_with_assigned_user():
    flash_msg = \
        'EVM Group "{}": Error during \'destroy\': Still has users assigned'
    group = new_group()
    group.create()
    user = new_user(group=group)
    user.create()
    with error.expected(flash_msg.format(group.description)):
        group.delete()


def test_edit_default_group():
    flash_msg = 'Read Only EVM Group "{}" can not be edited'
    group = ac.Group(description='EvmGroup-approver')
    sel.force_navigate("cfg_accesscontrol_groups")
    row = group_table.find_row_by_cells({'Name': group.description})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Edit the selected Group')
    flash.assert_message_match(flash_msg.format(group.description))


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
    sel.force_navigate("cfg_accesscontrol_groups")
    row = group_table.find_row_by_cells({'Name': group.description})
    original_sequence = sel.text(row.sequence)
    set_group_order([group.description])
    row = group_table.find_row_by_cells({'Name': group.description})
    changed_sequence = sel.text(row.sequence)
    assert original_sequence != changed_sequence, "Edit Sequence Failed"


# Role test cases
def test_role_crud():
    role = new_role()
    role.create()
    with update(role):
        role.name = role.name + "edited"
    copied_role = role.copy()
    copied_role.delete()
    role.delete()


def test_rolename_required_error_validation():
    role = ac.Role(
        name=None,
        vm_restriction='Only User Owned')
    with error.expected("Name can't be blank"):
        role.create()


def test_rolename_duplicate_validation():
    role = new_role()
    role.create()
    with error.expected("Name has already been taken"):
        role.create()


def test_delete_default_roles():
    flash_msg = \
        'Role "{}": Error during \'destroy\': Cannot delete record because of dependent miq_groups'
    role = ac.Role(name='EvmRole-approver')
    with error.expected(flash_msg.format(role.name)):
        role.delete()


def test_edit_default_roles():
    role = ac.Role(name='EvmRole-auditor')
    sel.force_navigate("cfg_accesscontrol_role_edit", context={"role": role})
    flash.assert_message_match("Read Only Role \"{}\" can not be edited" .format(role.name))


def test_delete_roles_with_assigned_group():
    flash_msg = \
        'Role "{}": Error during \'destroy\': Cannot delete record because of dependent miq_groups'
    role = new_role()
    role.create()
    group = new_group(role=role.name)
    group.create()
    with error.expected(flash_msg.format(role.name)):
        role.delete()


def test_assign_user_to_new_group():
    role = new_role()  # call function to get role
    role.create()
    group = new_group(role=role.name)
    group.create()
    user = new_user(group=group)
    user.create()


def _test_vm_provision():
    logger.info("Checking for provision access")
    sel.force_navigate("infra_vms")
    virtual_machines.lcl_btn("Provision VMs")


def _test_vm_power_on():
    """Ensures power button is shown for a VM"""
    logger.info("Checking for power button")
    vm_name = virtual_machines.Vm.get_first_vm_title()
    logger.debug("VM " + vm_name + " selected")
    if not virtual_machines.is_pwr_option_visible(vm_name, option=virtual_machines.Vm.POWER_ON):
        raise OptionNotAvailable("Power button does not exist")


def _test_vm_removal():
    logger.info("Testing for VM removal permission")
    vm_name = virtual_machines.get_first_vm()
    logger.debug("VM " + vm_name + " selected")
    virtual_machines.remove(vm_name, cancel=True)


@pytest.mark.parametrize(
    'product_features, action',
    [(
        {version.LOWEST: [['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Infrastructure', 'Virtual Machines', 'VM Access Rules',
             'Modify', 'Provision VMs']],
         '5.5': [['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
             'Provision VMs']]},
        _test_vm_provision)])
def test_permission_edit(request, product_features, action):
    """
    Ensures that changes in permissions are enforced on next login
    """
    product_features = version.pick(product_features)
    request.addfinalizer(login.login_admin)
    role_name = fauxfactory.gen_alphanumeric()
    role = ac.Role(name=role_name,
                  vm_restriction=None,
                  product_features=[(['Everything'], False)] +    # role_features
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
    login.login_admin()
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
    return lambda: ac.Role(name=name,
                           vm_restriction=vm_restriction,
                           product_features=product_features)


def _go_to(dest):
    """Create a thunk that navigates to the given destination"""
    return lambda: nav.go_to(dest)


cat_name = "Configure"


@pytest.mark.parametrize(
    'role,allowed_actions,disallowed_actions',
    [[_mk_role(product_features=[[['Everything'], False],  # minimal permission
                                 [['Everything', cat_name, 'Tasks'], True]]),
      {'tasks': lambda: sel.click(tasks.buttons.default)},  # can only access one thing
      {
          'my services': _go_to('my_services'),
          'chargeback': _go_to('chargeback'),
          'clouds providers': _go_to('clouds_providers'),
          'infrastructure providers': _go_to('infrastructure_providers'),
          'control explorer': _go_to('control_explorer'),
          'automate explorer': _go_to('automate_explorer')}],
     [_mk_role(product_features=[[['Everything'], True]]),  # full permissions
      {
          'my services': _go_to('my_services'),
          'chargeback': _go_to('chargeback'),
          'clouds providers': _go_to('clouds_providers'),
          'infrastructure providers': _go_to('infrastructure_providers'),
          'control explorer': _go_to('control_explorer'),
          'automate explorer': _go_to('automate_explorer')},
      {}]])
# @pytest.mark.meta(blockers=[1035399]) # work around instead of skip
@pytest.mark.meta(blockers=[1262759])
def test_permissions(role, allowed_actions, disallowed_actions):
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
            login.login(user)
            for name, action_thunk in allowed_actions.items():
                try:
                    action_thunk()
                except Exception:
                    fails[name] = "%s: %s" % (name, traceback.format_exc())
            for name, action_thunk in disallowed_actions.items():
                try:
                    with error.expected(Exception):
                        action_thunk()
                except error.UnexpectedSuccessException:
                    fails[name] = "%s: %s" % (name, traceback.format_exc())
            if fails:
                message = ''
                for failure in fails.values():
                    message = "%s\n\n%s" % (message, failure)
                raise Exception(message)
    finally:
        login.login_admin()


def single_task_permission_test(product_features, actions):
    """Tests that action succeeds when product_features are enabled, and
       fail when everything but product_features are enabled"""
    test_permissions(_mk_role(name=fauxfactory.gen_alphanumeric(),
                              product_features=[(['Everything'], False)] +
                              [(f, True) for f in product_features]),
                     actions,
                     {})
    test_permissions(_mk_role(name=fauxfactory.gen_alphanumeric(),
                              product_features=[(['Everything'], True)] +
                              [(f, False) for f in product_features]),
                     {},
                     actions)


@pytest.mark.meta(blockers=[1136112, 1262764])
def test_permissions_role_crud():
    single_task_permission_test([['Everything', cat_name, 'Configuration'],
                                 ['Everything', 'Services', 'Catalogs Explorer']],
                                {'Role CRUD': test_role_crud})


def test_permissions_vm_provisioning():
    features = version.pick({
        version.LOWEST: [
            ['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Modify',
                'Provision VMs']
        ],
        '5.5': [
            ['Everything', 'Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Everything', 'Access Rules for all Virtual Machines', 'VM Access Rules', 'Modify',
                'Provision VMs']
        ]})
    single_task_permission_test(
        features,
        {'Provision VM': _test_vm_provision}
    )


# This test is disabled until it has been rewritten
# def test_permissions_vm_power_on_access():
#    # Ensure VMs exist
#    if not virtual_machines.get_number_of_vms():
#        logger.debug("Setting up providers")
#        setup_first_provider()
#        logger.debug("Providers setup")
#    single_task_permission_test(
#        [
#            ['Infrastructure', 'Virtual Machines', 'Accordions'],
#            ['Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Operate', 'Power On']
#        ],
#        {'VM Power On': _test_vm_power_on}
#    )


# This test is disabled until it has been rewritten
# def test_permissions_vm_remove():
#    # Ensure VMs exist
#    if not virtual_machines.get_number_of_vms():
#        logger.debug("Setting up providers")
#        setup_infrastructure_providers()
#        logger.debug("Providers setup")
#    single_task_permission_test(
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
#     sel.force_navigate('cfg_accesscontrol_user_add')
#     pw = fauxfactory.gen_alphanumeric()
#     fill(ac.User.user_form, {
#         "name_txt": fauxfactory.gen_alphanumeric(),
#         "userid_txt": fauxfactory.gen_alphanumeric(),
#         "password_txt": pw,
#         "password_verify_txt": pw,
#         "email_txt": "test@test.test"
#     })
#     assert not sel.is_displayed(form_buttons.add), "The Add button should not be displayed!"


def test_user_change_password(request):
    user = ac.User(
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
    request.addfinalizer(login.login_admin)
    with user:
        assert not login.logged_in()
        login.login(user)
        assert login.current_full_name() == user.name
    login.login_admin()
    with update(user):
        user.credential = Credential(
            principal=user.credential.principal,
            secret="another_very_secret",
            verify_secret="another_very_secret",
        )
    with user:
        assert not login.logged_in()
        login.login(user)
        assert login.current_full_name() == user.name


# Tenant/Project test cases
@pytest.mark.uncollectif(lambda: version.current_version() < "5.5")
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
    tenant = ac.Tenant(
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


@pytest.mark.uncollectif(lambda: version.current_version() < "5.5")
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
    tenant = ac.Tenant(
        name='tenant1' + fauxfactory.gen_alphanumeric(),
        description='tenant1 description')
    project = ac.Project(
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


@pytest.mark.uncollectif(lambda: version.current_version() < "5.5")
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
        new_tenant = ac.Tenant(
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
