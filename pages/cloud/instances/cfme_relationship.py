# -*- coding: utf-8 -*-
# pylint: disable=R0904

from selenium.webdriver.common.by import By
from pages.base import Base

class CfmeRelationship(Base):
    """Edit CFME server relationship page"""
    _page_title = 'CloudForms Management Engine: Instances'
    _select_server_pulldown = (By.ID, "server_id")
    _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _reset_button_locator = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    def select_server(self, server_name):
        """Select cfme server from dropdown menu"""
        self.select_dropdown(server_name, *self._select_server_pulldown)

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
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)

    def click_on_cancel(self):
        """Click on cancel button"""
        self.cancel_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)

    def click_on_reset(self):
        """Click on reset button"""
        self._wait_for_visible_element(*self._reset_button_locator)
        self.reset_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.instances.details import Details
        return Details(self.testsetup)
