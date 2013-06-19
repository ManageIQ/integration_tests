# -*- coding: utf-8 -*-
from pages.page import Page
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taggable import Taggable
from pages.regions.policy_mixin import PolicyMixin

class PolicyMenu(Page):
    '''Add this mixin to your page in 3 easy steps:
        * import: from pages.regions.policy_menu import PolicyMenu
        * add to class: class MyClass(Base, PolicyMenu):
        * call methods directly from test or page
    '''
    # github issue filed to add IDs for consistent access
    # https://github.com/ManageIQ/cfme/issues/352
    _policy_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Policy']")
    _manage_policies_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title^='Manage Policies for']")
    _edit_tags_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title^='Edit Tags for']")

    @property
    def policy_button(self):
        return self.selenium.find_element(*self._policy_button_locator)

    @property
    def manage_policies_button(self):
        return self.selenium.find_element(*self._manage_policies_locator)

    @property
    def edit_tags_button(self):
        return self.selenium.find_element(*self._edit_tags_locator)

    def click_on_manage_policies(self):
        ActionChains(self.selenium).click(self.policy_button).click(self.manage_policies_button).perform()
        return PolicyMenu.ManagePolicies(self.testsetup)

    def click_on_edit_tags(self):
        ActionChains(self.selenium).click(self.policy_button).click(self.edit_tags_button).perform()
        return PolicyMenu.EditTags(self.testsetup)

    class EditTags(Base, Taggable):
        @property
        def save(self):
            return self.save_tag_edits

        @property
        def cancel(self):
            return self.cancel_tag_edits

        @property
        def reset(self):
            return self.reset_tag_edits

    class ManagePolicies(Base, PolicyMixin):
        @property
        def save(self):
            return self.save_policy_assignment

        @property
        def cancel(self):
            return self.cancel_policy_assignment

        @property
        def reset(self):
            return self.reset_policy_assignment


