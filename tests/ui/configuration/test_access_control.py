import pytest
import time
import random
from unittestzero import Assert

@pytest.fixture  # IGNORE:E1101
def ac_control_roles_pg(home_page_logged_in):
    configuration_pg = home_page_logged_in.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
    ac_pg = configuration_pg.click_on_access_control()
    Assert.true(ac_pg.is_the_current_page)
    return ac_pg.click_on_roles()

@pytest.fixture
def ac_control_groups_pg(home_page_logged_in):
    configuration_pg = home_page_logged_in.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
    ac_pg = configuration_pg.click_on_access_control()
    Assert.true(ac_pg.is_the_current_page)
    return ac_pg.click_on_groups()

@pytest.fixture
def ac_control_users_pg(home_page_logged_in):
    configuration_pg = home_page_logged_in.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
    ac_pg = configuration_pg.click_on_access_control()
    Assert.true(ac_pg.is_the_current_page)
    return ac_pg.click_on_users()

@pytest.fixture
def random_string():
    rand_string = ""
    letters = 'abcdefghijklmnopqrstuvwxyz'
    for i in xrange(8):
        rand_string += random.choice(letters)
    return rand_string

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestAccessControl:
    _roles_list = []
    _groups_list = []
    _users_list = []

    def test_add_new_role(self, mozwebqa, ac_control_roles_pg, random_string):
        roles_pg = ac_control_roles_pg
        add_new_role_pg = roles_pg.click_on_add_new()
        role_name = random_string
        self._roles_list.append(role_name)
        add_new_role_pg.fill_name(role_name)
        add_new_role_pg.select_access_restriction("user")
        roles_pg = add_new_role_pg.save()
        Assert.true(roles_pg.flash.message.startswith('Role "%s" was saved' % role_name))

    def test_edit_role(self, mozwebqa, ac_control_roles_pg, random_string):
        roles_pg = ac_control_roles_pg
        old_role_name = self._roles_list[0]
        select_role_pg = roles_pg.click_on_role(old_role_name)
        Assert.true(select_role_pg.role_name == old_role_name)
        edit_role_pg = select_role_pg.click_on_edit()
        new_role_name = random_string
        self._roles_list.remove(self._roles_list[0])
        self._roles_list.append(new_role_name)
        edit_role_pg.fill_name(new_role_name)
        edit_role_pg.select_access_restriction("user_or_group")
        roles_pg = edit_role_pg.save()
        Assert.true(roles_pg.flash.message.startswith('Role "%s" was saved' % new_role_name))
        
    def test_copy_role(self, mozwebqa, ac_control_roles_pg, random_string):
        roles_pg = ac_control_roles_pg
        select_role_name = self._roles_list[0]
        select_role_pg = roles_pg.click_on_role(select_role_name)
        Assert.true(select_role_pg.role_name == select_role_name)
        copy_role_pg = select_role_pg.click_on_copy()
        copy_role_name = random_string
        self._roles_list.append(copy_role_name)
        copy_role_pg.fill_name(copy_role_name)
        roles_pg = copy_role_pg.save()
        Assert.true(roles_pg.flash.message.startswith('Role "%s" was saved' % copy_role_name))
        

    def test_delete_role(self, mozwebqa, ac_control_roles_pg):
        roles_pg = ac_control_roles_pg 
        while len(self._roles_list) > 0:
            select_role_pg = roles_pg.click_on_role(self._roles_list[len(self._roles_list) - 1])
            Assert.true(select_role_pg.role_name == self._roles_list[len(self._roles_list) - 1])
            roles_pg = select_role_pg.click_on_delete()
            Assert.true(roles_pg.flash.message.startswith('Role "%s": Delete successful' % self._roles_list[len(self._roles_list) - 1]))
            self._roles_list.pop()

    def test_add_new_group(self, mozwebqa, ac_control_groups_pg, random_string):
        groups_pg = ac_control_groups_pg
        add_new_group_pg = groups_pg.click_on_add_new()
        group_name = random_string
        self._groups_list.append(group_name)        
        add_new_group_pg.fill_info(random_string, "EvmRole-administrator")
        groups_pg = add_new_group_pg.save()
        Assert.true(groups_pg.flash.message.startswith('Group "%s" was saved' % group_name))
        
    def test_edit_group(self, mozwebqa, ac_control_groups_pg, random_string):
        groups_pg = ac_control_groups_pg
        old_group_name = self._groups_list[0]
        select_group_pg = groups_pg.click_on_group(old_group_name)
        Assert.true(select_group_pg.group_name == old_group_name)
        edit_groups_pg = select_group_pg.click_on_edit()
        new_group_name = random_string
        self._groups_list.remove(self._groups_list[0])
        self._groups_list.append(new_group_name)
        edit_groups_pg.fill_info(new_group_name, "EvmRole-user")
        groups_pg = edit_groups_pg.save()
        Assert.true(groups_pg.flash.message.startswith('Group "%s" was saved' % new_group_name))
   
    def test_edit_group_tags(self, mozwebqa, ac_control_groups_pg):
        groups_pg = ac_control_groups_pg
        old_group_name = self._groups_list[0]
        select_group_pg = groups_pg.click_on_group(old_group_name)
        Assert.true(select_group_pg.group_name == old_group_name)
        edit_tags_pg = select_group_pg.click_on_edit_tags()
        edit_tags_pg.select_category("Cost Center")
        edit_tags_pg.select_value("Cost Center 001")
        groups_pg = edit_tags_pg.save
        Assert.true(select_group_pg.flash.message.startswith('Tag edits were successfully saved'))

    def test_delete_group(self, mozwebqa, ac_control_groups_pg):
        groups_pg = ac_control_groups_pg 
        while len(self._groups_list) > 0:
            select_group_pg = groups_pg.click_on_group(self._groups_list[len(self._groups_list) - 1])
            Assert.true(select_group_pg.group_name == self._groups_list[len(self._groups_list) - 1])
            groups_pg = select_group_pg.click_on_delete()
            Assert.true(groups_pg.flash.message.startswith('EVM Group "%s": Delete successful' % self._groups_list[len(self._groups_list) - 1]))
            self._groups_list.pop()


    def test_add_new_user(self, mozwebqa, ac_control_users_pg, random_string):
        users_pg = ac_control_users_pg
        add_new_user_pg = users_pg.click_on_add_new()
        user_name = random_string
        self._users_list.append(user_name)
        add_new_user_pg.fill_info(user_name, user_name, "test_pswd", "test_pswd", "test_email@email.com", "EvmGroup-administrator")
        users_pg = add_new_user_pg.click_on_add()
        Assert.true(users_pg.flash.message.startswith('User "%s" was saved' %user_name))

    def test_edit_user(self, mozwebqa, ac_control_users_pg, random_string):
        users_pg = ac_control_users_pg
        old_user_name = self._users_list[0]
        select_user_pg = users_pg.click_on_user(old_user_name)
        Assert.true(select_user_pg.user_name == old_user_name)
        edit_user_pg = select_user_pg.click_on_edit()
        new_user_name = random_string
        self._users_list.remove(self._users_list[0])
        self._users_list.append(new_user_name)
        edit_user_pg.fill_info(new_user_name, new_user_name, "", "", "", "EvmGroup-user")
        users_pg = edit_user_pg.click_on_save()
        Assert.true(users_pg.flash.message.startswith('User "%s" was saved' %new_user_name))

    def test_copy_user(self, mozwebqa, ac_control_users_pg, random_string):
        users_pg = ac_control_users_pg
        select_user_name = self._users_list[0]
        select_user_pg = users_pg.click_on_user(select_user_name)
        Assert.true(select_user_pg.user_name == select_user_name)
        copy_user_pg = select_user_pg.click_on_copy()
        copy_user_name = random_string
        self._users_list.append(copy_user_name)
        copy_user_pg.fill_info(copy_user_name, copy_user_name, "copy_pswd", "copy_pswd", "copy_email@email.com", "")
        copy_user_pg.click_on_add()
        Assert.true(users_pg.flash.message.startswith('User "%s" was saved' % copy_user_name))

    def test_edit_user_tags(self, mozwebqa, ac_control_users_pg):
        users_pg = ac_control_users_pg
        old_user_name = self._users_list[0]
        select_user_pg = users_pg.click_on_user(old_user_name)
        Assert.true(select_user_pg.user_name == old_user_name)
        edit_tags_pg = select_user_pg.click_on_edit_tags()
        edit_tags_pg.select_category("Cost Center")
        edit_tags_pg.select_value("Cost Center 001")
        edit_tags_pg.save
        Assert.true(select_user_pg.flash.message.startswith('Tag edits were successfully saved'))
   
    def test_delete_user(self, mozwebqa, ac_control_users_pg):
        users_pg = ac_control_users_pg
        while len(self._users_list) > 0:
            select_user_pg = users_pg.click_on_user(self._users_list[len(self._users_list) - 1])
            Assert.true(select_user_pg.user_name == self._users_list[len(self._users_list) - 1])
            users_pg = select_user_pg.click_on_delete()
            Assert.true(users_pg.flash.message.startswith('EVM User "%s": Delete successful' % self._users_list[len(self._users_list) - 1]))
            self._users_list.pop()

