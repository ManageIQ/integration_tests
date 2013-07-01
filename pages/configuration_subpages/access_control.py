'''
Access Control pages
'''
# -*- coding: utf-8 -*-

from pages.base import Base
from pages.page import Page
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taggable import Taggable
from pages.regions.taskbar.taskbar import TaskbarMixin

class AccessControl(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _roles_button = (By.CSS_SELECTOR, "div[title='View Roles']")
    _groups_button = (By.CSS_SELECTOR, "div[title='View Groups']")
    _users_button = (By.CSS_SELECTOR, "div[title='View Users']")

    class MixinBase(Page):
        _locator_suffix = ">td.td_btn_txt>div.btn_sel_text"
        _locator_css = """tr[title="%s"] %s"""

        def _get_button(self, title):
            _locator = (By.CSS_SELECTOR, self._locator_css
                    % (title, self._locator_suffix))
            return self.get_element(*_locator)

        def _click_on_configuration_subbutton(self, button, _class):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(button).perform()
            self._wait_for_results_refresh()
            return _class(self.testsetup)

        def _click_on_policy_subbutton(self, button, _class):
            ActionChains(self.selenium).click(self.policy_button)\
                    .click(button).perform()
            self._wait_for_results_refresh()
            return _class(self.testsetup)

    class UrgMixin(MixinBase):
        @property
        def add_button(self):
            return self._get_button(self._add_button_title)

        def _click_on_add_new(self, _new_class):
            return self._click_on_configuration_subbutton(
                    self.add_button, _new_class)

        def _click_on_type(self, name, _show_class):
            selector = "td[title='%s']" % name
            self.selenium.find_element_by_css_selector(selector).click()
            self._wait_for_results_refresh()
            return _show_class(self.testsetup)

    class EditTagsMixin(MixinBase):
        @property
        def edit_tags_button(self):
            return self._get_button(self._edit_tags_title)

        def _click_on_edit_tags(self, _edit_tags_class):
            return self._click_on_policy_subbutton(
                    self.edit_tags_button, _edit_tags_class)

    def __click_on_main_section(self, cls, *locator):
        self.get_element(*locator).click()
        self._wait_for_results_refresh()
        return cls(self.testsetup)

    # ROLES
    def click_on_roles(self):
        return self.__click_on_main_section(self.Roles, *self._roles_button)

    class Roles(Base, TaskbarMixin, UrgMixin):
        _page_title = 'CloudForms Management Engine: Configuration'
        _add_button_title = 'Add a new Role'

        def click_on_add_new(self):
            return self._click_on_add_new(AccessControl.NewRole)

        def click_on_role(self, role_name):
            return self._click_on_type(role_name, AccessControl.ShowRole)

    class NewRole(Base):
        _submit_role_button = (By.CSS_SELECTOR, "img[alt='Add']")
        _name_field = (By.CSS_SELECTOR, "input[name='name']")
        _access_restriction_field = (By.CSS_SELECTOR,
                "select[name='vm_restriction']")
        _product_features_tree = (By.ID, "new__everything")

        @property
        def product_features(self):
            return CheckboxTree(self.testsetup,
                    self.selenium.find_element(*self._product_features_tree))

        def fill_name(self, name):
            field = self.selenium.find_element(*self._name_field)
            field.clear()
            return field.send_keys(name)

        def save(self):
            # when editing an existing role, wait until "save" button shows up
            # after ajax validation
            self._wait_for_visible_element(*self._submit_role_button)
            self.selenium.find_element(*self._submit_role_button).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowRole(self.testsetup)

        def select_access_restriction(self, value):
            Select(self.selenium.find_element(*self._access_restriction_field)).select_by_value(value)

    class EditRole(NewRole):
        _name_field = (By.CSS_SELECTOR, "input[name='name']")
        _submit_role_button = (By.CSS_SELECTOR, "img[title='Save Changes']")

        def fill_name(self, name):
            field = self.selenium.find_element(*self._name_field)
            field.clear()
            field.send_keys(name)

    class ShowRole(Base, TaskbarMixin):
        _edit_role_button = (By.CSS_SELECTOR,
                "tr[title='Edit this Role'] > td.td_btn_txt > div.btn_sel_text")
        _delete_role_button = (By.CSS_SELECTOR,
                "tr[title='Delete this Role'] > td.td_btn_txt > \
                        div.btn_sel_text")
        _copy_role_button = (By.CSS_SELECTOR,
                "tr[title='Copy this Role to a new Role'] > td.td_btn_txt > \
                        div.btn_sel_text")
        _role_name_label = (By.CSS_SELECTOR,
                ".style1 tr:nth-child(1) td:nth-child(2)")

        @property
        def edit_button(self):
            return self.get_element(*self._edit_role_button)

        @property
        def delete_button(self):
            return self.get_element(*self._delete_role_button)

        @property
        def copy_button(self):
            return self.get_element(*self._copy_role_button)

        def click_on_edit(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.edit_button).perform()
            self._wait_for_results_refresh()
            return AccessControl.EditRole(self.testsetup)

        def click_on_delete(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.delete_button).perform()
            self.handle_popup()
            self._wait_for_results_refresh()
            return AccessControl.Roles(self.testsetup)
        
        def click_on_copy(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.copy_button).perform()
            self._wait_for_results_refresh()
            return AccessControl.NewRole(self.testsetup)

        @property
        def role_name(self):
            return self.selenium.find_element(*self._role_name_label).text.strip()


    # GROUPS
    def click_on_groups(self):
        return self.__click_on_main_section(self.Groups, *self._groups_button)

    class Groups(Base, TaskbarMixin, UrgMixin):
        _page_title = 'CloudForms Management Engine: Configuration'
        _add_button_title = 'Add a new Group'

        def click_on_add_new(self):
            return self._click_on_add_new(AccessControl.NewGroup)

        def click_on_group(self, group_name):
            return self._click_on_type(group_name, AccessControl.ShowGroup)

    class NewGroup(Base):
        _submit_group_button = (By.CSS_SELECTOR, "img[alt='Add']")
        _group_description_field = (By.ID, "description")
        _role_selector= (By.ID, "group_role")
        _company_tags_tree = (By.CSS_SELECTOR, "#myco_treebox")
        _hosts_clusters_tree = (By.CSS_SELECTOR, "#hac_treebox")
        _vms_templates_tree = (By.CSS_SELECTOR, "#vat_treebox")

        @property
        def company_tags(self):
            return CheckboxTree(self.testsetup, self.selenium.find_element(*self._company_tags_tree))

        @property
        def hosts_clusters(self):
            return CheckboxTree(self.testsetup, self.selenium.find_element(*self._hosts_clusters_tree))

        @property
        def vms_templates(self):
            return CheckboxTree(self.testsetup, self.selenium.find_element(*self._vms_templates_tree))

        def fill_info(self, description, role):
            self.selenium.find_element(*self._group_description_field).send_keys(description)
            return self.select_dropdown(role, *self._role_selector)

        def save(self):
            # when editing an existing group, wait until "save" button shows up
            # after ajax validation
            self._wait_for_visible_element(*self._submit_group_button)
            self.selenium.find_element(*self._submit_group_button).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowGroup(self.testsetup)

    class EditGroup(NewGroup):
        _group_description_field = (By.ID, "description")
        _role_selector= (By.ID, "group_role")
        _submit_group_button = (By.CSS_SELECTOR, "img[title='Save Changes']")

        def fill_info(self, description, role):
            field = self.selenium.find_element(*self._group_description_field)
            field.clear()
            field.send_keys(description)
            return self.select_dropdown(role, *self._role_selector)

    class ShowGroup(Base, EditTagsMixin, TaskbarMixin):
        _edit_group_button = (By.CSS_SELECTOR,
                "tr[title='Edit this Group'] > td.td_btn_txt > \
                div.btn_sel_text")
        _delete_group_button = (By.CSS_SELECTOR,
                "tr[title='Delete this Group'] > td.td_btn_txt > \
                div.btn_sel_text")
        _group_name_label = (By.CSS_SELECTOR,
                ".style1 tr:nth-child(1) td:nth-child(2)")
        _edit_tags_title = "Edit 'My Company' Tags for this Group"

        @property
        def edit_button(self):
            return self.get_element(*self._edit_group_button)

        @property
        def delete_button(self):
            return self.get_element(*self._delete_group_button)

        def click_on_edit(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.edit_button).perform()
            self._wait_for_results_refresh()
            return AccessControl.EditGroup(self.testsetup)

        def click_on_delete(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.delete_button).perform()
            self.handle_popup()
            self._wait_for_results_refresh()
            return AccessControl.Groups(self.testsetup)
        
        def click_on_edit_tags(self):
            return self._click_on_edit_tags(AccessControl.TagGroup)

        @property
        def group_name(self):
            return self.selenium.find_element(
                    *self._group_name_label).text.strip()

    class TagGroup(Base, Taggable):
        _cancel_edits_button = (
                By.CSS_SELECTOR, "div#buttons_off img[title='Cancel']"
)
    # USERS
    def click_on_users(self):
        return self.__click_on_main_section(self.Users, *self._users_button)

    class Users(Base, TaskbarMixin, UrgMixin):
        _page_title = 'CloudForms Management Engine: Configuration'
        _add_button_title = 'Add a new User'

        def click_on_add_new(self):
            return self._click_on_add_new(AccessControl.NewEditUser)

        def click_on_user(self, user_name):
            return self._click_on_type(user_name, AccessControl.ShowUser)

    class NewEditUser(Base):
        _submit_user_button = (By.CSS_SELECTOR, "img[alt='Add']")
        _save_user_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
        _user_name_field = (By.ID, "name")
        _user_id_field= (By.ID, "userid")
        _user_password_field = (By.ID, "password")
        _user_confirm_password_field = (By.ID, "password2")
        _user_email_field = (By.ID, "email")
        _user_group_selector = (By.ID, "chosen_group")

        def fill_info(self, name, userid, pswd, pswd2, email, group):
            if(name):
                field = self.selenium.find_element(*self._user_name_field)
                field.clear()
                field.send_keys(name)
            if(userid):
                field = self.selenium.find_element(*self._user_id_field)
                field.clear()
                field.send_keys(userid)
            if(pswd):
                field = self.selenium.find_element(*self._user_password_field)
                field.clear()
                field.send_keys(pswd)
            if(pswd2):
                field = self.selenium.find_element(*self._user_confirm_password_field)
                field.clear()
                field.send_keys(pswd2)
            if(email):
                field = self.selenium.find_element(*self._user_email_field)
                field.clear()
                field.send_keys(email)
            if(group):
                self.select_dropdown(group, *self._user_group_selector)

        def click_on_add(self):
            # when editing an existing group, wait until "save" button shows up
            # after ajax validation
            self._wait_for_visible_element(*self._submit_user_button)
            self.selenium.find_element(*self._submit_user_button).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowUser(self.testsetup)
        
        def click_on_save(self):
            self._wait_for_visible_element(*self._save_user_button)
            self.selenium.find_element(*self._save_user_button).click()
            self._wait_for_results_refresh()
            return AccessControl.ShowUser(self.testsetup)

    class ShowUser(Base, EditTagsMixin, TaskbarMixin, Taggable):
        _edit_user_button = (By.CSS_SELECTOR,
                "tr[title='Edit this User'] > td.td_btn_txt > div.btn_sel_text")
        _delete_user_button = (By.CSS_SELECTOR,
                "tr[title='Delete this User'] > td.td_btn_txt > \
                div.btn_sel_text")
        _copy_user_button = (By.CSS_SELECTOR,
                "tr[title='Copy this User to a new User'] > \
                td.td_btn_txt > div.btn_sel_text")
        _edit_tags_title = "Edit 'My Company' Tags for this User"
        _user_name_label = (By.CSS_SELECTOR, ".style1 tr:nth-child(1) td:nth-child(2)")

        @property
        def edit_user_button(self):
            return self.get_element(*self._edit_user_button)

        @property
        def delete_user_button(self):
            return self.get_element(*self._delete_user_button)

        @property
        def copy_user_button(self):
            return self.get_element(*self._copy_user_button)

        def click_on_edit(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.edit_user_button).perform()
            self._wait_for_results_refresh()
            return AccessControl.NewEditUser(self.testsetup)

        def click_on_delete(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.delete_user_button).perform()
            self.handle_popup()
            self._wait_for_results_refresh()
            return AccessControl.Users(self.testsetup)
        
        def click_on_copy(self):
            ActionChains(self.selenium).click(self.configuration_button)\
                    .click(self.copy_user_button).perform()
            self._wait_for_results_refresh()
            return AccessControl.NewEditUser(self.testsetup)

        def click_on_edit_tags(self):
            return self._click_on_edit_tags(AccessControl.TagUser)

        @property
        def user_name(self):
            return self.selenium.find_element(*self._user_name_label).text.strip()

    class TagUser(Base, Taggable):
        _cancel_edits_button = (
                By.CSS_SELECTOR, "div#buttons_off img[title='Cancel']")
