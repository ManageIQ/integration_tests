# -*- coding: utf-8 -*-

from cfme.configure import access_control as ac
from utils import randomness as random
from utils.update import update


def new_group():
    return ac.Group(description='grp' + random.generate_random_string(),
                    group_role_select='EvmRole-approver')


def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
    group.delete()
