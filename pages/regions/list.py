'''
Created on May 6, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class ListRegion(Page):
    '''Represents a table list region'''
    _items_locator = (By.CSS_SELECTOR, "tr")

    def __init__(self, testsetup, root, cls):
        Page.__init__(self, testsetup, root)
        self._item_cls = cls

    @property
    def items(self):
        '''Returns a list of items represented by _item_cls'''
        return [self._item_cls(self.testsetup, web_element)
                for web_element in self._root_element.find_elements(
                        *self._items_locator)]

class ListItem(Page):
    '''Represents an item in the list'''
    _item_data_locator = (By.CSS_SELECTOR, "td")

    def click(self):
        '''Click on the item, which will select it in the list'''
        self._item_data[0].click()
        self._wait_for_results_refresh()

    @property
    def _item_data(self):  # IGNORE:C0111
        return [web_element
                for web_element in self._root_element.find_elements(
                        *self._item_data_locator)]

