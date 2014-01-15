import pytest

from utils.randomness import generate_random_string


@pytest.fixture
def groups_pg(cnf_configuration_pg):
    ac_pg = cnf_configuration_pg.click_on_access_control()
    return ac_pg.click_on_groups()


@pytest.fixture(scope='module')
def group_name():
    return generate_random_string()


def test_access_control_add_new_group(groups_pg, group_name):
    add_new_group_pg = groups_pg.click_on_add_new()
    add_new_group_pg.fill_info(group_name, "EvmRole-administrator")
    groups_pg = add_new_group_pg.save()
    assert 'was saved' in groups_pg.flash.message.lower()
    assert group_name in groups_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_group')
def test_access_control_edit_group(groups_pg, group_name):
    new_group_name = generate_random_string()
    select_group_pg = groups_pg.click_on_group(group_name)

    # Change the group name
    edit_groups_pg = select_group_pg.click_on_edit()
    edit_groups_pg.fill_info(new_group_name, "EvmRole-user")
    groups_pg = edit_groups_pg.save()
    assert 'was saved' in groups_pg.flash.message.lower()
    assert new_group_name in groups_pg.flash.message

    # Change it back for future tests
    edit_groups_pg = select_group_pg.click_on_edit()
    edit_groups_pg.fill_info(group_name, "EvmRole-administrator")
    groups_pg = edit_groups_pg.save()
    assert 'was saved' in groups_pg.flash.message.lower()
    assert group_name in groups_pg.flash.message


@pytest.mark.requires_test('test_access_control_add_new_group')
def test_access_control_edit_group_tags(groups_pg, group_name):
    select_group_pg = groups_pg.click_on_group(group_name)
    edit_tags_pg = select_group_pg.click_on_edit_tags()
    tag_cat, tag_value = edit_tags_pg.add_random_tag()
    assert edit_tags_pg.is_tag_displayed(tag_cat, tag_value)

    edit_tags_pg.save_tag_edits()
    assert 'tag edits were successfully saved' in groups_pg.flash.message.lower()


@pytest.mark.requires_test('test_access_control_add_new_group')
def test_access_control_delete_group(groups_pg, group_name):
    select_group_pg = groups_pg.click_on_group(group_name)
    groups_pg = select_group_pg.click_on_delete()
    assert 'delete successful' in groups_pg.flash.message.lower()
    assert group_name in groups_pg.flash.message
