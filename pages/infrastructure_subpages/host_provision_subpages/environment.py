# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.host_provision import HostProvisionFormButtonMixin
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select


class HostProvisionEnvironment(Base, HostProvisionFormButtonMixin):
    '''Represents the Environment tab in the Provision VM wizard'''
    _provider_select_locator = (
        By.ID, "environment__placement_ems_name")
    _cluster_select_locator = (
        By.ID, "environment__placement_cluster_name")
    _datastore_list_locator = (
        By.CSS_SELECTOR, "div#prov_ds_div > table > tbody")

    @property
    def provider(self):
        '''Provider - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._provider_select_locator))

    @property
    def cluster(self):
        '''Cluster - Name

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._cluster_select_locator))

    @property
    def datastore_list(self):
        '''Returns the datastore list region'''
        return ListRegion(
            self.testsetup,
            self.get_element(*self._datastore_list_locator),
            self.DatastoreItem)

    def click_on_datastore_item(self, item_name):
        '''Select datastore item by name'''
        datastore_items = self.datastore_list.items
        selected_item = \
            datastore_items[[item for item in range(len(datastore_items))
            if datastore_items[item].name == item_name][0]]
        selected_item.click()
        self._wait_for_results_refresh()
        return self.DatastoreItem(selected_item)

    def fill_fields(self, provider_name, cluster_name, datastore_list):
        self.provider.select_by_visible_text(provider_name)
        self._wait_for_results_refresh()
        self.cluster.select_by_visible_text(cluster_name)
        self._wait_for_results_refresh()
        for ds_item in datastore_list:
            self.click_on_datastore_item(ds_item)
        return HostProvisionEnvironment(self.testsetup)

    class DatastoreItem(ListItem):
        '''Represents a datastore in the list'''
        _columns = ["name", "free_space", "total_space"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def free_space(self):
            return self._item_data[1].text

        @property
        def total_space(self):
            return self._item_data[2].text
