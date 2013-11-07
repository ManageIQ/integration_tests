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
    _security_groups_locator = (By.ID, "hardware__security_groups")
    _security_groups_option_locator = (By.CSS_SELECTOR,
            "select#hardware__security_groups > option[value='23000000000011']")
    _cloud_watch_select_locator = (
            By.ID, "hardware__monitoring")
    _public_ip_address_select_locator = (By.ID, "hardware__floating_ip_address")

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
    def security_groups(self):
        '''Security Groups - EC2'''
        return self.get_element(*self._security_groups_locator)

    @property
    def security_groups_option(self):
        '''Security Groups Option for default'''
        return self.get_element(*self._security_groups_option_locator)

    @property
    def cloud_watch_selector(self):
        '''Cloud Watch monitoring'''
        return Select(self.get_element(*self._cloud_watch_select_locator))

    @property
    def public_address_select(self):
        '''Floating Public IP - Openstack'''
        return Select(
                self.get_element(*self. _public_ip_address_select_locator))

    def fill_fields(
            self,
            instance_type,
            key_pair,
            security_group,
            public_ip):
        # self.instance_type_select.select_by_visible_text(instance_type)
        self.instance_type_select.select_by_index(instance_type)
        self._wait_for_results_refresh()
        self.guest_access_select.select_by_visible_text(key_pair)
        self._wait_for_results_refresh()
        #self.security_groups.select_by_index(security_group)
        self.security_groups.click()
        self._wait_for_results_refresh()
        if public_ip is not None:
            self.public_address_select.select_by_visible_text(public_ip)
            self._wait_for_results_refresh()
        return ProvisionProperties(self.testsetup)

