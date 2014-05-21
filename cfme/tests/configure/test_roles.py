# -*- coding: utf-8 -*-

from cfme.configure import access_control as ac
from utils import randomness as random
from utils.update import update


def new_role():
    return ac.Role(name='rol' + random.generate_random_string(),
                   vm_restriction_select='None')


def test_role_crud():
    role = new_role()
    role.create()
    with update(role):
        role.name = role.name + "edited"
    role.delete()
