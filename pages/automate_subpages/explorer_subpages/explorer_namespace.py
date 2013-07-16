# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.support.select import Select
from time import sleep

class ExplorerNamespace(Base):
    _configuration_button = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _remove_namespaces_button = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Remove selected Namespaces']")
    _namespace_list_locator = (By.CSS_SELECTOR, "div#ns_list_grid_div > div.objbox > table > tbody")
    _name_text_field = (By.ID, "ns_name")
    _description_text_field = (By.ID, "ns_description")
    _add_system_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")


    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button)

    @property
    def remove_namespaces_button(self):
        return self.selenium.find_element(*self._remove_namespaces_button)

    @property
    def namespace_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._namespace_list_locator),
                 ExplorerNamespace.NamespaceItem)

    @property
    def add_namespace_button(self):
        return self.selenium.find_element(*self._add_namespace_button)

    def click_on_remove_selected_namespaces(self):
        self._wait_for_results_refresh()
        ActionChains(self.selenium).click(self.configuration_button).click(self.remove_namespaces_button).perform()
        self.handle_popup(cancel=False)
        return ExplorerNamespace(self.testsetup)

    def click_on_namespace_item(self, item_name):
        namespace_items = self.namespace_list.items
        selected_item = None
        for i in range(1, len(namespace_items)):
            if namespace_items[i]._item_data[2].text == item_name:
                selected_item = namespace_items[i]
                namespace_items[i]._item_data[0].find_element_by_tag_name('img').click()
        self._wait_for_results_refresh()
        return ExplorerNamespace.NamespaceItem(selected_item)

    def fill_namespace_info(self, namespace_name, namespace_description):
        self.selenium.find_element(*self._name_text_field).send_keys(namespace_name)
        self.selenium.find_element(*self._description_text_field).send_keys(namespace_description)
        self._wait_for_visible_element(*self._add_system_button)
        self.selenium.find_element(*self._add_system_button).click()
        self._wait_for_results_refresh()
        from pages.automate import Automate
        return Automate.Explorer(self.testsetup)


    class NamespaceItem(ListItem):
        '''Represents a namespace in the list'''
        _columns = ["checkbox", "folder", "name", "description"]

        @property
        def checkbox(self):
            pass

        @property
        def folder(self):
            pass

        @property
        def iname(self):
            return self._item_data[2].text

        @property
        def description(self):
            pass


