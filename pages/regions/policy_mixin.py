# -*- coding: utf-8 -*-
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from pages.regions.checkboxtree import Checkbox
from pages.regions.list import ListRegion, ListItem


class PolicyMixin(Page):
    '''This is included in the PolicyMenu mixin so you get this 
       functionality any time PolicyMenu is included in your class
    '''
    _save_changes_button = (By.CSS_SELECTOR, "a[title='Save Changes']")
    _cancel_changes_button = (By.CSS_SELECTOR, "a[title='Cancel']")
    _reset_changes_button = (By.CSS_SELECTOR, "a[title='Reset Changes']")

    def save_policy_assignment(self):
        self._wait_for_visible_element(*self._save_changes_button)
        self.selenium.find_element(*self._save_changes_button).click()
        self._wait_for_results_refresh()

    def cancel_policy_assignment(self):
        self._wait_for_visible_element(*self._cancel_changes_button)
        self.selenium.find_element(*self._cancel_changes_button).click()
        self._wait_for_results_refresh()

    def reset_policy_assignment(self):
        self._wait_for_visible_element(*self._reset_changes_button)
        self.selenium.find_element(*self._reset_changes_button).click()
        self._wait_for_results_refresh()

    def select_profile_item(self, profile):
        '''Select profile checkbox'''
        item = self.item_by_name(profile)
        item.check()
        self._wait_for_results_refresh()

    def deselect_profile_item(self, profile):
        '''Deselect profile checkbox'''
        item = self.item_by_name(profile)
        item.uncheck()
        self._wait_for_results_refresh()

    def item_by_name(self, profile):
        '''get profile item from list by name'''
        profile_items = self.profile_list.items
        return profile_items[[item for item in range(len(profile_items)) if profile_items[item].name == profile][0]]

    @property
    def profile_list(self):
        '''Returns the template list region'''
        _root_item_locator = (By.CSS_SELECTOR, "div#treebox > div > table > tbody")
        return ListRegion(
                self.testsetup,
                self.get_element(*_root_item_locator),
                self.ProfileItem)

    class ProfileItem(ListItem, Checkbox):
        '''Represents an item in the profile list'''

        @property
        def name(self):
            '''Profile name'''
            return self._item_data[3].text.encode('utf-8')
