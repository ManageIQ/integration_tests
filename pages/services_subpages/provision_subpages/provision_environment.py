'''
Created on May 6, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from time import sleep

class ProvisionEnvironment(Base):
    '''Represents the Environment tab in the Provision VM wizard'''
    _place_automatically_checkbox_locator = (
            By.ID, "environment__placement_auto")
    _datacenter_select_locator = (
            By.ID, "environment__placement_dc_name")
    _cluster_select_locator = (
            By.ID, "environment__placement_cluster_name")
    _resource_pool_select_locator = (
            By.ID, "environment__placement_rp_name")
    _folder_name_select_locator = (
            By.ID, "environment__placement_folder_name")
    _host_filter_select_locator = (
            By.ID, "environment__host_filter")
    _host_name_list_locator = (
            By.CSS_SELECTOR, "div#prov_host_div > table > tbody")
    _datastore_create_checkbox_locator = (
            By.ID, "environment__new_datastore_create")
    _datastore_filter_select_locator = (
            By.ID, "environment__ds_filter")
    _datastore_list_locator = (
            By.CSS_SELECTOR, "div#prov_ds_div > table > tbody")

    @property
    def choose_automatically(self):
        '''VM Placement - Choose automatically'''
        return self.get_element(*self._place_automatically_checkbox_locator)

    @property
    def datacenter(self):
        '''Datacenter - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._datacenter_select_locator))

    @property
    def cluster(self):
        '''Cluster - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._cluster_select_locator))

    @property
    def resource_pool(self):
        '''Resource Pool - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._resource_pool_select_locator))

    @property
    def folder_name(self):
        '''Folder - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._folder_name_select_locator))

    @property
    def host_filter(self):
        '''Host - Filter

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._host_filter_select_locator))

    @property
    def host_list(self):
        '''Returns the host list region'''
        return ListRegion(
                self.testsetup,
                self.get_element(*self._host_name_list_locator),
                self.HostItem)

    @property
    def datastore_create(self):
        '''Datastore - Create'''
        return self.get_element(*self._datastore_create_checkbox_locator)

    @property
    def datastore_filter(self):
        '''Datastore - Filter'''
        return Select(self.get_element(*self._datastore_filter_select_locator))

    @property
    def datastore_list(self):
        '''Returns the datastore list region'''
        return ListRegion(
                self.testsetup,
                self.get_element(*self._datastore_list_locator),
                self.DatastoreItem)

    def click_on_host_item(self, item_name):
            '''Select host item from list by name'''
            host_items = self.host_list.items
            sleep(6)
            selected_item = host_items[[item for item in range(len(host_items)) if host_items[item].name == item_name][0]]
            selected_item.click()
            self._wait_for_results_refresh()
            return self.HostItem(selected_item)

    def click_on_datastore_item(self, item_name):
            '''Select datastore item by name'''
            datastore_items = self.datastore_list.items
            selected_item = datastore_items[[item for item in range(len(datastore_items)) if datastore_items[item].name == item_name][0]]
            selected_item.click()
            self._wait_for_results_refresh()
            return self.DatastoreItem(selected_item)

    def fill_fields(self, host_name, datastore_name):
            self.click_on_host_item(host_name)
            self.click_on_datastore_item(datastore_name)
            self._wait_for_results_refresh()
            return ProvisionEnvironment(self.testsetup)

    class HostItem(ListItem):
        '''Represents a host in the list'''
        _columns = ["name", "total_vms", "platform", "version", "state"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def total_vms(self):
            pass

        @property
        def platform(self):
            pass

        @property
        def version(self):
            pass

        @property
        def state(self):
            pass

    class DatastoreItem(ListItem):
        '''Represents a datastore in the list'''
        _columns = ["name", "free_space", "total_space"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def free_space(self):
            pass

        @property
        def total_space(self):
            pass

