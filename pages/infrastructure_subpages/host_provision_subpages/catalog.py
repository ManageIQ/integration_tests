# -*- coding: utf-8 -*-

from pages.base import Base
from pages.infrastructure_subpages.host_provision import HostProvisionFormButtonMixin
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select


class HostProvisionCatalog(Base, HostProvisionFormButtonMixin):
    '''Represents the Catalog tab in the Provision wizard'''
    _pxe_server_select_locator = (By.ID, "service__pxe_server_id")
    _pxe_image_list_locator = (By.CSS_SELECTOR, "div#prov_pxe_img_div > table > tbody")
    _host_list_locator = (By.CSS_SELECTOR, "div#prov_host_div > table > tbody")

    @property
    def host_list(self):
        '''Select - Host'''
        return ListRegion(self.testsetup, self.get_element(*self._host_list_locator),
            self.HostItem)

    @property
    def server_image_pxe_list(self):
        '''Select - PXE Image'''
        return ListRegion(self.testsetup,
            self.get_element(*self._pxe_image_list_locator),
            self.ServerImageItem)

    @property
    def provision_type(self):
        '''Select - Provision Type

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._provision_type_select_locator))

    @property
    def pxe_server(self):
        '''Select - PXE Server

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._pxe_server_select_locator))

    def select_host(self, host_name):
        host_items = self.host_list.items
        for item in host_items:
            if item.name == host_name:
                item.click()
                self._wait_for_results_refresh()
                return item
        else:
            return None

    def select_server_image(self, server_image_name):
        si_items = self.server_image_pxe_list.items
        selected_item = None
        for i in range(1, len(si_items)):
            if si_items[i].name == server_image_name:
                selected_item = si_items[i]
                selected_item.click()
        self._wait_for_results_refresh()
        return HostProvisionCatalog.ServerImageItem(selected_item)

    def fill_fields(
            self,
            pxe_server_name,
            server_image_name,
            host_name):
        '''Fill fields on Catalog page'''
        self.select_host(host_name)
        self._wait_for_results_refresh()
        self.pxe_server.select_by_visible_text(pxe_server_name)
        self._wait_for_results_refresh()

        self.select_server_image(server_image_name)
        return HostProvisionCatalog(self.testsetup)

    class ServerImageItem(ListItem):
        '''Represents a server image item from the list'''
        _columns = ["name", "description"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def description(self):
            return self._item_data[1].text

    class HostItem(ListItem):
        _columns = ["name", "mac_address"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def mac_address(self):
            return self._item_data[1].text
