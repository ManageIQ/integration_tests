import pytest

from utils.randomness import generate_random_string


@pytest.fixture
def users_pg(cnf_configuration_pg):
    ac_pg = cnf_configuration_pg.click_on_access_control()
    return ac_pg.click_on_users()


@pytest.fixture(scope='module')
def user_name():
    return generate_random_string()


@pytest.fixture(scope='module')
def other_user_name():
    # An "other" user name target for edit/copy tests
    return generate_random_string()


def test_access_control_add_new_user(users_pg, user_name):
    add_new_user_pg = users_pg.click_on_add_new()
    add_new_user_pg.fill_info(user_name, user_name, "test_pswd", "test_pswd",
        "test_email@email.com", "EvmGroup-administrator")
    users_pg = add_new_user_pg.click_on_add()
    assert 'was saved' in users_pg.flash.message.lower()
    assert user_name in users_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_user')
def test_access_control_edit_user(users_pg, user_name, other_user_name):
    select_user_pg = users_pg.click_on_user(user_name)
    edit_user_pg = select_user_pg.click_on_edit()
    edit_user_pg.fill_info(other_user_name, other_user_name, "", "", "", "EvmGroup-user")
    users_pg = edit_user_pg.click_on_save()
    assert 'was saved' in users_pg.flash.message.lower()
    assert other_user_name in users_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_user')
def test_access_control_copy_user(users_pg, user_name, other_user_name):
    select_user_pg = users_pg.click_on_user(other_user_name)
    copy_user_pg = select_user_pg.click_on_copy()
    copy_user_pg.fill_info(user_name, user_name, "copy_pswd", "copy_pswd",
        "copy_email@email.com", "")
    copy_user_pg.click_on_add()
    assert 'was saved' in users_pg.flash.message.lower()
    assert user_name in users_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_user')
def test_access_control_edit_user_tags(users_pg, user_name):
    select_user_pg = users_pg.click_on_user(user_name)
    edit_tags_pg = select_user_pg.click_on_edit_tags()
    tag_cat, tag_value = edit_tags_pg.add_random_tag()
    assert edit_tags_pg.is_tag_displayed(tag_cat, tag_value)

    edit_tags_pg.save_tag_edits()
    assert 'were successfully saved' in edit_tags_pg.flash.message.lower()


@pytest.mark.requires_test('test_access_control_add_new_user')
def test_access_control_delete_user(users_pg, user_name, other_user_name):
    for current_user_name in (user_name, other_user_name):
        select_user_pg = users_pg.click_on_user(current_user_name)
        users_pg = select_user_pg.click_on_delete()
        assert 'delete successful' in users_pg.flash.message.lower()
        assert current_user_name in users_pg.flash.message
