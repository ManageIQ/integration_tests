# -*- coding: utf-8 -*-
import pytest
import cfme.configure.access_control as ac
from utils.update import update
import utils.error as error
import utils.randomness as random
import cfme.fixtures.pytest_selenium as sel
from cfme import Credential
from cfme import login
from cfme.web_ui.menu import nav
from cfme.configure import tasks
from utils import version

usergrp = ac.Group(description='EvmGroup-user')


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


def test_user_login():
    pytest.skip('https://bugzilla.redhat.com/show_bug.cgi?id=1098343')
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


cat_name = version.pick({"default": "Settings & Operations",
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
          'automate explorer': _go_to('automate_explorer'),
      }],
     [_mk_role(product_features=[[['Everything'], True]]),  # full permissions
      {
          'my services': _go_to('my_services'),
          'chargeback': _go_to('chargeback'),
          'clouds providers': _go_to('clouds_providers'),
          'infrastructure providers': _go_to('infrastructure_providers'),
          'control explorer': _go_to('control_explorer'),
          'automate explorer': _go_to('automate_explorer'),
      },
      {}]])
def test_permissions(role, allowed_actions, disallowed_actions):
    # pytest.skip('https://bugzilla.redhat.com/show_bug.cgi?id=1098343')
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
            except Exception as e:
                fails[name] = e
        for name, action_thunk in disallowed_actions.items():
            try:
                with error.expected(Exception):
                    action_thunk()
            except error.UnexpectedSuccessException as e:
                fails[name] = e
        if fails:
            raise Exception(fails)
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
    single_task_permission_test([['Settings & Operations', 'Configuration'],
                                 ['Services', 'Catalogs Explorer']],
                                {'Role CRUD': test_role_crud})
