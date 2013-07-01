'''
Created on May 31, 2013

@author: bcrochet
'''
# -*- coding: utf8 -*-
from pages.base import Base
from selenium.webdriver.common.by import By

# pylint: disable=C0103
# pylint: disable=W0142

class ProvidersDiscovery(Base):
    '''Infrastructure Providers Discovery Page'''
    _page_title = 'CloudForms Management Engine: Infrastructure Providers'
    _start_button_locator = (By.CSS_SELECTOR, "input[name='start']")
    _cancel_button_locator = (By.CSS_SELECTOR, "input[name='cancel']")
    _provider_type_locator = {
        "virtualcenter" : (
                By.CSS_SELECTOR,
                "input[name='discover_type_virtualcenter']"),
        "rhevm"         : (
                By.CSS_SELECTOR, "input[name='discover_type_rhevm']")
    }

    _from_first_locator = (By.CSS_SELECTOR, "input[name='from_first']")
    _from_second_locator = (By.CSS_SELECTOR, "input[name='from_second']")
    _from_third_locator = (By.CSS_SELECTOR, "input[name='from_third']")
    _from_fourth_locator = (By.CSS_SELECTOR, "input[name='from_fourth']")

    _to_fourth_locator = (By.CSS_SELECTOR, "input[name='to_fourth']")

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
        from pages.infrastructure_subpages.providers import Providers
        return Providers(self.testsetup)

    def click_on_cancel(self):
        '''Click on the cancel button'''
        self.selenium.find_element(*self._cancel_button_locator).click()
        from pages.infrastructure_subpages.providers import Providers
        return Providers(self.testsetup)

    def discover_infrastructure_providers(
            self,
            provider_type,
            from_address,
            to_address):
        '''Discover infrastructure providers'''
        self.mark_checkbox(
                self._provider_type_locator[provider_type])
        from_ip = from_address.split('.')
        to_ip = to_address.split('.')
        self.selenium.find_element(
                *self._from_first_locator).send_keys(from_ip[0])
        self.selenium.find_element(
                *self._from_second_locator).send_keys(from_ip[1])
        self.selenium.find_element(
                *self._from_third_locator).send_keys(from_ip[2])
        self.selenium.find_element(
                *self._from_fourth_locator).send_keys(from_ip[3])
        self.selenium.find_element(
                *self._to_fourth_locator).send_keys(to_ip[3])
        return self.click_on_start()

