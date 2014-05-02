#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pytest
import cfme.configure.access_control as ac
from cfme.web_ui import flash
from utils.update import update
import utils.error as error
import utils.randomness as random


def new_user():
    return ac.User(username = 'user' + random.generate_random_string(),
                    userid =  'uid' + random.generate_random_string(),
                    password = 'redhat',
                    password_verify= 'redhat',
                    email = 'xyz@redhat.com',
                    user_group_select = 'EvmGroup-user',
                    cost_center_select = 'Workload',
                    value_assign_select = 'Database')


def new_group():
    return ac.Group(description = 'grp' + random.generate_random_string(),
                     group_role_select = 'EvmRole-approver')


def new_role():
    return ac.Role(name = 'rol' + random.generate_random_string(),
                     vm_restriction_select = 'None')


@pytest.mark.nondestructive
def test_add_new_user():
        nu = new_user()
        nu.create()


def test_edit_user():
        ue = new_user()
        ue.create()
        with update(ue):
            ue.username = ue.username + "-edited"
            ue.userid = ue.userid + "edited"


def test_copy_user():
        uc = new_user()
        uc.create()
        uc.copy()


def test_delete_user():
        du = new_user()
        du.create()
        du.delete()


def test_user_duplicate_name():
        nu = new_user()
        nu.create()
        with error.expected("Userid has already been taken"):
            nu.create()


def test_add_new_group():
        ng = new_group()
        ng.create()


def test_edit_group():
        ge = new_group()
        ge.create()
        with update(ge):
            ge.description = ge.description + "edited"


def test_delete_group():
        gd = new_group()
        gd.create()
        gd.delete()


def test_add_new_role():
        nr = new_role()
        nr.create()


def test_edit_role():
        re = new_role()
        re.create()
        with update(re):
            re.name = re.name + "edited"


def test_delete_role():
        rd = new_role()
        rd.create()
        rd.delete()
