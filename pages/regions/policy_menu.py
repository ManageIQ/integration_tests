# -*- coding: utf-8 -*-
from pages.page import Page
from pages.base import Base
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
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
    _manage_policies_locator = (By.CSS_SELECTOR,
        "table.buttons_cont tr[title^='Manage Policies for']")
    # dajo - 130826 - opting for img locator, found inconsitent text capitialization on some menus
    _edit_tags_locator = (By.CSS_SELECTOR,
        "table.buttons_cont td img[src='/images/toolbars/tag.png']")

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
        ActionChains(self.selenium).click(self.policy_button).click(
            self.manage_policies_button).perform()
        return PolicyMenu.ManagePolicies(self.testsetup)

    def click_on_edit_tags(self):
        ActionChains(self.selenium).click(self.policy_button).click(self.edit_tags_button).perform()
        self._wait_for_visible_element(*Taggable._tag_category_selector)
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
        checkbox = "//table/tbody/tr/td/span[@class='standartTreeRow']" \
            "[contains(text(), '%s')]/../../td[@width='16px']/img"

        def policy_selected(self, policy_name):
            try:
                e = self.selenium.find_element_by_xpath(self.checkbox % policy_name)
                return "Uncheck" not in e.get_attribute("src")
            except (NoSuchElementException, TypeError):
                return False

        def save(self, visible_timeout=None):
            """ Clicks on the Save button.

            @keyword visible_timeout: Modify standard timeout for button's appearance.
            """
            self.save_policy_assignment(visible_timeout=visible_timeout)

        def cancel(self, visible_timeout=None):
            """ Clicks on the Cancel button.

            @keyword visible_timeout: Modify standard timeout for button's appearance.
            """
            self.cancel_policy_assignment(visible_timeout=visible_timeout)

        def reset(self, visible_timeout=None):
            """ Clicks on the Reset button.

            @keyword visible_timeout: Modify standard timeout for button's appearance.
            """
            self.reset_policy_assignment(visible_timeout=visible_timeout)
