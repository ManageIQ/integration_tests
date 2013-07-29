'''
Created on May 2, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from unittestzero import Assert

class ProvisionCatalog(Base, ProvisionFormButtonMixin):
    '''Represents the Catalog tab in the Provision wizard'''
    _filter_select_locator = (By.ID, "service__vm_filter")
    _name_list_locator = (
            By.CSS_SELECTOR, "div#prov_vm_div > table > tbody")
    _provision_type_select_locator = (By.ID, "service__provision_type")
    _pxe_server_select_locator = (By.ID, "service__pxe_server_id")
    _linked_clone_checkbox_locator = (By.ID, "service__linked_clone")
    _pxe_image_list_locator = (
            By.CSS_SELECTOR, "div#prov_pxe_img_div > table > tbody")
    _number_of_vms_select_locator = (By.ID, "service__number_of_vms")
    _vm_name_locator = (By.ID, "service__vm_name")
    _vm_description_locator = (By.ID, "service__vm_description")
    _vm_description_char_count_locator = (
            By.CSS_SELECTOR, "span#description_count")

    @property
    def catalog_filter(self):
        '''Select - Filter

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._filter_select_locator))

    @property
    def catalog_list(self):
        '''Select - Name

        Returns a list region
        '''
        return ListRegion(self.testsetup,
                self.get_element(*self._name_list_locator),
                self.CatalogItem)

    @property
    def server_image_pxe_list(self):
        return ListRegion(self.testsetup,
                self.get_element(*self._pxe_image_list_locator),
                self.CatalogItem)

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



    @property
    def linked_clone(self):
        '''Select - Linked Clone'''
        return self.get_element(*self._linked_clone_checkbox_locator)

    @property
    def number_of_vms(self):
        '''Number of VMs

        Returns a Select webelement
        '''
        return Select(self.get_element(*self._number_of_vms_select_locator))

    @property
    def vm_name(self):
        '''VM Naming - Name'''
        return self.get_element(*self._vm_name_locator)

    @property
    def vm_description(self):
        '''VM Naming - Description'''
        return self.get_element(*self._vm_description_locator)

    @property
    def vm_description_count(self):
        '''VM Naming - Description character count'''
        return self.get_element(*self._vm_description_char_count_locator)

    def select_server_image(self, server_image_name):
        si_items = self.server_image_pxe_list.items
        selected_item = None
        for i in range(1, len(si_items)):
            if si_items[i].name == server_image_name:
                selected_item = si_items[i]
                selected_item.click()
        self._wait_for_results_refresh()
        return ProvisionCatalog.ServerImageItem(selected_item)

    def fill_fields(
            self,
            provision_type_text,
            pxe_server_name,
            server_image_name,
            number_of_vms_text,
            vm_name_text,
            vm_description_text):
        '''Fill fields on Catalog page'''
        self.provision_type.select_by_visible_text(provision_type_text)
        self._wait_for_results_refresh()
        if 'PXE' in provision_type_text:
            self.pxe_server.select_by_visible_text(pxe_server_name)
            self._wait_for_results_refresh()
        if server_image_name:
            self.select_server_image(server_image_name)
        self.number_of_vms.select_by_visible_text(number_of_vms_text)
        self._wait_for_visible_element(*self._vm_name_locator)
        self.vm_name.send_keys(vm_name_text)
        self.vm_description.send_keys(vm_description_text)
        Assert.equal(self.vm_description_count.text,
                unicode(len(vm_description_text)),
                "Description count does not match size of description text")
        return ProvisionCatalog(self.testsetup)

    class CatalogItem(ListItem):
        '''Represents a catalog item from the list'''
        _columns = ["name", "operating_system", "platform", "cpus", "memory",
                "disk_size", "management_system", "snapshots"]

        @property
        def name(self):
            '''Template name'''
            return self._item_data[0].text

        @property
        def operating_system(self):
            '''Template operating system'''
            return self._item_data[1].text

        @property
        def platform(self):
            '''Template platform'''
            return self._item_data[2].text

        @property
        def cpus(self):
            '''Template CPU count'''
            return self._item_data[3].text

        @property
        def memory(self):
            '''Template memory'''
            return self._item_data[4].text

        @property
        def disk_size(self):
            '''Template disk size'''
            return self._item_data[5].text

        @property
        def management_system(self):
            '''Template management system'''
            return self._item_data[6].text

        @property
        def snapshots(self):
            '''Template snapshot count'''
            return self._item_data[7].text


    class ServerImageItem(ListItem):
        '''Represents a server image item from the list'''
        _columns = ["name", "description"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def description(self):
            return self._item_data[1].text

