# -*- coding: utf8 -*-
from pages.base import Base
from selenium.webdriver.common.by import By

# pylint: disable=C0103
# pylint: disable=R0904

class Discovery(Base):
    '''Cloud Providers Discovery Page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'
    _start_button_locator = (By.CSS_SELECTOR, "input[name='start']")
    _cancel_button_locator = (By.CSS_SELECTOR, "input[name='cancel']")
    _username_locator = (By.ID, 'userid')
    _password_locator = (By.ID, 'password')
    _password_verify_locator = (By.ID, 'verify')
    _form_title_locator = (By.CSS_SELECTOR, "div.dhtmlxInfoBarLabel-2")

    @property
    def form_title(self):
        ''' Fetch the form title on the page '''
        return self.selenium.find_element(*self._form_title_locator).text

    def is_selected(self, checkbox_locator):
        '''Is the checkbox locator selected?'''
        return self.selenium.find_element(*checkbox_locator).is_selected()

    def toggle_checkbox(self, checkbox_locator):
        '''Toggle the checkbox'''
        self.selenium.find_element(*checkbox_locator).click()

    def mark_checkbox(self, checkbox_locator):
        '''Set the check'''
        if not self.is_selected(checkbox_locator):
            self.toggle_checkbox(checkbox_locator)

    def unmark_checkbox(self, checkbox_locator):
        '''Unset the check'''
        if self.is_selected(checkbox_locator):
            self.toggle_checkbox(checkbox_locator)

    def click_on_start(self):
        '''Click on the start discovery button'''
        self.selenium.find_element(*self._start_button_locator).click()
        from pages.cloud.providers import Providers
        return Providers(self.testsetup)

    def click_on_cancel(self):
        '''Click on the cancel button'''
        self.selenium.find_element(*self._cancel_button_locator).click()
        from pages.cloud.providers import Providers
        return Providers(self.testsetup)

    def _fill_in_discovery_form(
            self,
            username,
            password,
            password_verify):
        ''' Fill in discovery form'''

        self.selenium.find_element(
                *self._username_locator).send_keys(username)
        self.selenium.find_element(
                *self._password_locator).send_keys(password)
        self.selenium.find_element(
                *self._password_verify_locator).send_keys(password_verify)

    def discover_cloud_providers(
            self,
            username,
            password,
            password_verify):
        '''Discover Cloud Providers (EC2)'''

        self._fill_in_discovery_form(username, password, password_verify)
        return self.click_on_start()

    def discover_cloud_providers_and_cancel(
            self,
            username,
            password,
            password_verify):
        '''Discover Cloud Providers (EC2)'''

        self._fill_in_discovery_form(username, password, password_verify)
        return self.click_on_cancel()
