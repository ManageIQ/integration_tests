# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from pages.cloud.instances.details import Details
from pages.base import Base

class Ownership(Base):
    """Set Ownership for template"""
    _page_title = 'CloudForms Management Engine: Virtual Machines'
    _select_owner_pulldown = (By.ID, "user_name")
    _select_group_pulldown = (By.ID, "group_name")
    _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_button_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    def select_user_ownership(self, user_owner=None):
        """Select a user as the template owner, if defined"""
        if user_owner is not None:
            self.select_dropdown(user_owner, *self._select_owner_pulldown)

    def select_group_ownership(self, group_owner=None):
        """Select a user group as the template owner, if defined"""
        if group_owner is not None:
            self.select_dropdown(group_owner, *self._select_group_pulldown)

    @property
    def save_button(self):
        """Save button"""
        return self.get_element(*self._save_button_locator)

    @property
    def cancel_button(self):
        """Cancel button"""
        return self.get_element(*self._cancel_button_locator)

    @property
    def reset_button(self):
        """Reset button"""
        return self.get_element(*self._reset_button_locator)

    def click_on_save(self):
        """Click on save button"""
        self._wait_for_visible_element(*self._save_button_locator)
        self.save_button.click()
        self._wait_for_results_refresh()
        return Details(self.testsetup)

    def click_on_cancel(self):
        """Click on cancel button"""
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return Details(self.testsetup)

    def click_on_reset(self):
        """Click on reset button"""
        self._wait_for_visible_element(*self._reset_button_locator)
        self.reset_button.click()
        self._wait_for_results_refresh()
        return Details(self.testsetup)
