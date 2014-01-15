import pytest

from utils.randomness import generate_random_string


@pytest.fixture  # IGNORE:E1101
def roles_pg(cnf_configuration_pg):
    ac_pg = cnf_configuration_pg.click_on_access_control()
    return ac_pg.click_on_roles()


@pytest.fixture(scope='module')
def role_name():
    return generate_random_string()


@pytest.fixture(scope='module')
def other_role_name():
    # An "other" role name target for edit/copy tests
    return generate_random_string()


def test_access_control_add_new_role(roles_pg, role_name):
    add_new_role_pg = roles_pg.click_on_add_new()
    add_new_role_pg.fill_name(role_name)
    add_new_role_pg.select_access_restriction("user")
    roles_pg = add_new_role_pg.save()
    assert 'was saved' in roles_pg.flash.message.lower()
    assert role_name in roles_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_role')
def test_access_control_edit_role(roles_pg, role_name, other_role_name):
    select_role_pg = roles_pg.click_on_role(role_name)
    edit_role_pg = select_role_pg.click_on_edit()
    edit_role_pg.fill_name(other_role_name)
    edit_role_pg.select_access_restriction("user_or_group")
    roles_pg = edit_role_pg.save()
    assert 'was saved' in roles_pg.flash.message.lower()
    assert other_role_name in roles_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_role')
def test_access_control_copy_role(roles_pg, role_name, other_role_name):
    select_role_pg = roles_pg.click_on_role(other_role_name)
    copy_role_pg = select_role_pg.click_on_copy()
    copy_role_pg.fill_name(role_name)
    roles_pg = copy_role_pg.save()
    assert 'was saved' in roles_pg.flash.message.lower()
    assert role_name in roles_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_role')
def test_access_control_delete_role(roles_pg, role_name, other_role_name):
    for current_role_name in (role_name, other_role_name):
        select_role_pg = roles_pg.click_on_role(current_role_name)
        roles_pg = select_role_pg.click_on_delete()
        assert 'delete successful' in roles_pg.flash.message.lower()
        assert current_role_name in roles_pg.flash.message
