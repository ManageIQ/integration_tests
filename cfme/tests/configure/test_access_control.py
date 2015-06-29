# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import traceback
import cfme.configure.access_control as ac
import utils.error as error
import cfme.fixtures.pytest_selenium as sel
from cfme import Credential
from cfme import login
from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure import virtual_machines
from cfme.web_ui.menu import nav
from cfme.configure import tasks
from utils.blockers import BZ
from utils.log import logger
from utils.providers import setup_a_provider
from utils.update import update
from xml.sax.saxutils import quoteattr

usergrp = ac.Group(description='EvmGroup-user')


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
        login.login(user.credential.principal, user.credential.secret)
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
    with error.expected("Password_digest can't be blank"):
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
    row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
        "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
    tag = sel.text(row).strip()
    assert tag == "Cost Center: Cost Center 001", "User edit tag failed"
    user.delete()


def test_user_remove_tag():
    user = new_user()
    user.create()
    sel.force_navigate("cfg_accesscontrol_user_ed", context={"user": user})
    row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
        "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
    tag = sel.text(row).strip()
    user.edit_tags("Department", "Engineering")
    user.remove_tag("Department", "Engineering")
    assert tag != "Department: Engineering", "Remove User tag failed"
    user.delete()


# Group test cases
def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
    group.delete()


def test_group_edit_tag():
    group = new_group()
    group.create()
    group.edit_tags("Cost Center *", "Cost Center 001")
    row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
        "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
    tag = sel.text(row).strip()
    assert tag == "Cost Center: Cost Center 001", "Group edit tag failed"
    group.delete()


def test_group_remove_tag():
    group = new_group()
    group.create()
    sel.force_navigate("cfg_accesscontrol_group_ed", context={"group": group})
    row = sel.elements("//*[(self::th or self::td) and normalize-space(.)={}]/../.."
        "//td[img[contains(@src, 'smarttag')]]".format(quoteattr("My Company Tags")))
    tag = sel.text(row).strip()
    group.edit_tags("Department", "Engineering")
    group.remove_tag("Department", "Engineering")
    assert tag != "Department: Engineering", "Remove Group tag failed"
    group.delete()


# Role test cases
def test_role_crud():
    role = new_role()
    role.create()
    with update(role):
        role.name = role.name + "edited"
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
    vm_name = virtual_machines.get_first_vm_title()
    logger.debug("VM " + vm_name + " selected")
    if not virtual_machines.is_pwr_option_visible(vm_name, option=virtual_machines.Vm.POWER_ON):
        raise OptionNotAvailable("Power button does not exist")


def _test_vm_removal():
    logger.info("Testing for VM removal permission")
    vm_name = virtual_machines.get_first_vm()
    logger.debug("VM " + vm_name + " selected")
    virtual_machines.remove(vm_name, cancel=True)


@pytest.mark.parametrize('product_features, action',
                        [([['Infrastructure', 'Virtual Machines', 'Accordions'],
                          ['Infrastructure', 'Virtual Machines', 'VM Access Rules',
                           'Modify', 'Provision VMs']],
                        _test_vm_provision)])
def test_permission_edit(request, product_features, action):
    """
    Ensures that changes in permissions are enforced on next login
    """
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
    login.login(user.credential.principal, user.credential.secret)
    try:
        action()
    except Exception:
        pytest.fail('Incorrect permissions set')
    login.login_admin()
    role.update({'product_features': [(['Everything'], True)] +
                                     [(k, False) for k in product_features]
                 })
    login.login(user.credential.principal, user.credential.secret)
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
                                 [[cat_name, 'Tasks'], True]]),
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
        login.login(user.credential.principal, user.credential.secret)
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


@pytest.mark.meta(blockers=[1136112])
def test_permissions_role_crud():
    single_task_permission_test([[cat_name, 'Configuration'],
                                 ['Services', 'Catalogs Explorer']],
                                {'Role CRUD': test_role_crud})


def test_permissions_vm_provisioning():
    single_task_permission_test(
        [
            ['Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Modify', 'Provision VMs']
        ],
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
    login.logout()
    assert not login.logged_in()
    login.login(user.credential.principal, user.credential.secret)
    assert login.current_full_name() == user.name
    login.login_admin()
    with update(user):
        user.credential = Credential(
            principal=user.credential.principal,
            secret="another_very_secret",
            verify_secret="another_very_secret",
        )
    login.logout()
    assert not login.logged_in()
    login.login(user.credential.principal, user.credential.secret)
    assert login.current_full_name() == user.name
