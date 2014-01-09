'''
Created on October 30, 2013

@author: rlandy
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select


class ProvisionProperties(Base, ProvisionFormButtonMixin):
    '''Provision Wizard - Properies tab'''
    _instance_type_select_locator = (By.ID, "hardware__instance_type")
    _guest_access_select_locator = (By.ID, "hardware__guest_access_key_pair")
    _cloud_watch_select_locator = (By.ID, "hardware__monitoring")

    @property
    def instance_type_select(self):
        '''Type of instance to provision'''
        return Select(
            self.get_element(*self._instance_type_select_locator))

    @property
    def guest_access_select(self):
        '''Key Pair'''
        return Select(
            self.get_element(*self._guest_access_select_locator))

    @property
    def cloud_watch_selector(self):
        '''Cloud Watch monitoring'''
        return Select(self.get_element(*self._cloud_watch_select_locator))

    def fill_fields(
            self,
            instance_type,
            key_pair):
        '''Fills field entries in the Properties tab'''
        self.instance_type_select.select_by_index(instance_type)
        self._wait_for_results_refresh()
        self.guest_access_select.select_by_visible_text(key_pair)
        return ProvisionProperties(self.testsetup)
