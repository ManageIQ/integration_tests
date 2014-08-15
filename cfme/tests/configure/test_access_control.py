# -*- coding: utf-8 -*-
import pytest
import traceback
import cfme.configure.access_control as ac
import utils.error as error
import utils.randomness as random
import cfme.fixtures.pytest_selenium as sel
from cfme import Credential
from cfme import login
from cfme.exceptions import OptionNotAvailable
from cfme.infrastructure import virtual_machines
from cfme.web_ui.menu import nav
from cfme.configure import tasks
from utils import version
from utils.log import logger
from utils.providers import setup_infrastructure_providers
from utils.update import update

usergrp = ac.Group(description='EvmGroup-user')


# due to pytest.mark.bugzilla(1035399), non admin users can't login
# with no providers added
pytestmark = [pytest.mark.usefixtures("setup_cloud_providers")]


def new_credential():
    return Credential(principal='uid' + random.generate_random_string(), secret='redhat')


def new_user(group=usergrp):
    return ac.User(name='user' + random.generate_random_string(),
                   credential=new_credential(),
                   email='xyz@redhat.com',
                   group=group,
                   cost_center='Workload',
                   value_assign='Database')


def new_group(role='EvmRole-approver'):
    return ac.Group(description='grp' + random.generate_random_string(),
                    role=role)


def new_role():
    return ac.Role(name='rol' + random.generate_random_string(),
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


# @pytest.mark.bugzilla(1035399) # work around instead of skip
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
        name='user' + random.generate_random_string(),
        credential=Credential(principal=None, secret='redhat'),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Userid can't be blank"):
        user.create()


def test_user_password_required_error_validation():
    user = ac.User(
        name='user' + random.generate_random_string(),
        credential=Credential(principal='uid' + random.generate_random_string(), secret=None),
        email='xyz@redhat.com',
        group=group_user)
    with error.expected("Password_digest can't be blank"):
        user.create()


@pytest.mark.bugzilla(
    1118040, unskip={1118040: lambda appliance_version: appliance_version < "5.3"})
def test_user_group_error_validation():
    user = ac.User(
        name='user' + random.generate_random_string(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=None)
    with error.expected("A User must be assigned to a Group"):
        user.create()


def test_user_email_error_validation():
    user = ac.User(
        name='user' + random.generate_random_string(),
        credential=new_credential(),
        email='xyzdhat.com',
        group=group_user)
    with error.expected("Email must be a valid email address"):
        user.create()


# Group test cases
def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
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
    '''Ensures power button is shown for a VM'''
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
def test_permission_edit(product_features, action):
    '''
    Ensures that changes in permissions are enforced on next login
    '''
    role_name = random.generate_random_string()
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
    '''Create a thunk that returns a Role object to be used for perm
       testing.  name=None will generate a random name

    '''
    name = name or random.generate_random_string()
    return lambda: ac.Role(name=name,
                           vm_restriction=vm_restriction,
                           product_features=product_features)


def _go_to(dest):
    '''Create a thunk that navigates to the given destination'''
    return lambda: nav.go_to(dest)


cat_name = version.pick({version.LOWEST: "Settings & Operations",
                         "5.3": "Configure"})


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
# @pytest.mark.bugzilla(1035399) # work around instead of skip
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
    '''Tests that action succeeds when product_features are enabled, and
       fail when everything but product_features are enabled'''
    test_permissions(_mk_role(name=random.generate_random_string(),
                              product_features=[(['Everything'], False)] +
                              [(f, True) for f in product_features]),
                     actions,
                     {})
    test_permissions(_mk_role(name=random.generate_random_string(),
                              product_features=[(['Everything'], True)] +
                              [(f, False) for f in product_features]),
                     {},
                     actions)


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


def test_permissions_vm_power_on_access():
    # Ensure VMs exist
    if not virtual_machines.get_number_of_vms():
        logger.debug("Setting up providers")
        setup_infrastructure_providers()
        logger.debug("Providers setup")
    single_task_permission_test(
        [
            ['Infrastructure', 'Virtual Machines', 'Accordions'],
            ['Infrastructure', 'Virtual Machines', 'VM Access Rules', 'Operate', 'Power On']
        ],
        {'VM Power On': _test_vm_power_on}
    )


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
