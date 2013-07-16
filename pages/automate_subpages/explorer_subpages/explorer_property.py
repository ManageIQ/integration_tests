# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from time import sleep

class ExplorerProperty(Base):

    _properties_table_locator = (By.CSS_SELECTOR, "fieldset > table > tbody")

    @property
    def properties_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._properties_table_locator),
                 ExplorerProperty.PropertiesItem)


    def retrieve_properties_values(self, selected_property):
        property_items = self.properties_list.items
        selected_item= None
        for i in range(0, len(property_items)):
             if property_items[i]._item_data[0].text == selected_property:
                 selected_item = property_items[i]
        return selected_item._item_data[1].text

    class PropertiesItem(ListItem):
        '''Represents a property in the list'''
        _columns = ["prop", "prop_text"]

        @property
        def prop(self):
            return self._item_data[0].text

        @property
        def prop_text(self):
            return self._item_data[1].text



