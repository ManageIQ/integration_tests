# -*- coding: utf-8 -*-


from functools import partial

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, Region, Select, Tree, accordion, fill, flash
from cfme.web_ui.menu import nav
from utils.update import Updateable


def make_tree_locator(acc_name, root_name):
    return '//span[.="%s"]/../..//table//tr[contains(@title, "%s")]/../..' % (acc_name, root_name)

access_tree = Tree(make_tree_locator("Access Control", "Region"))


def make_button(button_title):
    """ Precise button factory. Targets only buttons that are visible.

    """
    return "//div[@id='buttons_on']/ul[@id='form_buttons']/li/img[@title='%s']" % button_title

crud_buttons = Region(
    locators={
        'save_button': make_button("Save Changes"),
        'reset_button': make_button("Reset Changes"),
        'cancel_button': make_button("Cancel"),
        'add_button': make_button("Add"),
    },
    identifying_loc="//div[@id='buttons_on']/ul[@id='form_buttons']",
)


tb_select = partial(tb.select, "Configuration")
#pol_btn = partial(tb.select, "Policy")
nav.add_branch('configuration',
               {'configuration_accesscontrol':
                [nav.fn(partial(accordion.click, "Access Control")),
                 {'cfg_accesscontrol_users':
                  [lambda d: access_tree.click_path("Users"),
                   {'cfg_accesscontrol_user_add':
                    lambda d: tb.select("Configuration", "Add a new User")}],

                  'cfg_accesscontrol_user_ed':
                  [lambda ctx: access_tree.click_path('Users', ctx.username),
                   {'cfg_accesscontrol_user_edit': lambda d: tb_select('Edit this User')}],

                  'cfg_accesscontrol_groups':
                  [lambda d: access_tree.click_path("Groups"),
                   {'cfg_accesscontrol_group_add':
                    lambda d: tb.select("Configuration", "Add a new Group")}],

                  'cfg_accesscontrol_group_ed':
                  [lambda ctx: access_tree.click_path('Groups', ctx.description),
                   {'cfg_accesscontrol_group_edit': lambda d: tb_select('Edit this Group')}],

                  'cfg_accesscontrol_Roles':
                  [lambda d: access_tree.click_path("Roles"),
                   {'cfg_accesscontrol_role_add':
                    lambda d: tb.select("Configuration", "Add a new Role")}],

                  'cfg_accesscontrol_role_ed':
                  [lambda ctx: access_tree.click_path('Roles', ctx.name),
                   {'cfg_accesscontrol_role_edit': lambda d: tb_select('Edit this Role')}],

                  }],

                'chargeback_assignments': nav.fn(partial(accordion.click, "Assignments"))})


class User(Updateable):
        user_form = Form(
            fields=[
                ('username', "//*[@id='name']"),
                ('userid', "//*[@id='userid']"),
                ('password', "//*[@id='password']"),
                ('password_verify', "//*[@id='password2']"),
                ('email', "//*[@id='email']"),
                ('user_group_select', Select("//*[@id='chosen_group']")),
            ])

        user_tag_form = Form(
            fields=[
                ('cost_center_select', Select("//*[@id='tag_cat']")),
                ('value_assign_select', Select("//*[@id='tag_add']")),
            ])

        def __init__(self, username=None, userid=None, password=None, password_verify=None,
                     email=None, user_group_select=None, cost_center_select=None,
                     value_assign_select=None):
            self.username = username
            self.userid = userid
            self.password = password
            self.password_verify = password
            self.email = email
            self.user_group_select = user_group_select
            self.cost_center_select = cost_center_select
            self.value_assign_select = value_assign_select

        def create(self):
            sel.force_navigate('cfg_accesscontrol_user_add')
            fill(self.user_form, self.__dict__, action=crud_buttons.add_button)
            flash.assert_success_message('User "%s" was saved' % self.username)

        def update(self, updates):
            sel.force_navigate("cfg_accesscontrol_user_edit", context=self)
            fill(self.user_form, updates, action=crud_buttons.save_button)
            flash.assert_success_message(
                'User "%s" was saved' % updates.get('username', self.username))

        def copy(self):
            form_data = {'username': self.username + "copy",
                         'userid': self.userid + "copy",
                         'password': "redhat",
                         'password_verify': "redhat"}
            sel.force_navigate("cfg_accesscontrol_user_ed", context=self)
            tb.select('Configuration', 'Copy this User to a new User')
            fill(self.user_form, form_data, action=crud_buttons.add_button)
            flash.assert_success_message('User "%s" was saved' % form_data['username'])
            copied_user = User(
                username=form_data['username'],
                userid=form_data['userid'],
                password=form_data['password'],
                password_verify=form_data['password_verify'])
            return copied_user

        def delete(self):
            sel.force_navigate("cfg_accesscontrol_user_ed", context=self)
            tb.select('Configuration', 'Delete this User', invokes_alert=True)
            sel.handle_alert()
            flash.assert_success_message('EVM User "%s": Delete successful' % self.username)


class Group(Updateable):
        group_form = Form(
            fields=[
                ('description', "//*[@id='description']"),
                ('group_role_select', Select("//*[@id='group_role']")),
            ])

        def __init__(self, description=None, group_role_select=None):
            self.description = description
            self.group_role_select = group_role_select

        def create(self):
            sel.force_navigate('cfg_accesscontrol_group_add')
            fill(self.group_form, self.__dict__, action=crud_buttons.add_button)
            flash.assert_message_match('Group "%s" was saved' % self.description)

        def update(self, updates):
            sel.force_navigate("cfg_accesscontrol_group_edit", context=self)
            fill(self.group_form, updates, action=crud_buttons.save_button)
            flash.assert_message_match(
                'Group "%s" was saved' % updates.get('description', self.description))

        def delete(self):
            sel.force_navigate("cfg_accesscontrol_group_ed", context=self)
            tb_select('Delete this Group', invokes_alert=True)
            sel.handle_alert()
            flash.assert_message_match('EVM Group "%s": Delete successful' % self.description)


class Role(Updateable):
        role_form = Form(
            fields=[
                ('name', "//*[@id='name']"),
                ('vm_restriction_select', Select("//*[@id='vm_restriction']")),
            ])

        def __init__(self, name=None, vm_restriction_select=None):
            self.name = name
            self.vm_restriction_select = vm_restriction_select

        def create(self):
            sel.force_navigate('cfg_accesscontrol_role_add')
            fill(self.role_form, self.__dict__, action=crud_buttons.add_button)
            flash.assert_message_match('Role "%s" was saved' % self.name)

        def update(self, updates):
            sel.force_navigate("cfg_accesscontrol_role_edit", context=self)
            fill(self.role_form, updates, action=crud_buttons.save_button)
            flash.assert_message_match('Role "%s" was saved' % updates.get('name', self.name))

        def delete(self):
            sel.force_navigate("cfg_accesscontrol_role_ed", context=self)
            tb_select('Delete this Role', invokes_alert=True)
            sel.handle_alert()
            flash.assert_message_match('Role "%s": Delete successful' % self.name)
