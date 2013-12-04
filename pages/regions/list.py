# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
import fixtures.pytest_selenium as sel


def extract_row(row_loc, fn=sel.text):
    '''Extract row as a list, passing each item
    through fn'''
    return map(fn, sel.element(row_loc).find_elements_by_xpath('./td'))


def extract_table(table_loc, fn=sel.text):
    '''Extract table as a list of lists, passing
    each item through fn.
    '''
    return [extract_row(row, fn) for row in
            sel.element(table_loc).find_elements(By.CSS_SELECTOR, "tr")]


def as_dict(table_data):
    '''Converts rows into a dict, where the key is the first item in each row
    and the value is the rest of the items.
    '''
    return {row[0]: row[1:] for row in table_data}

# class ListRegion(Page):
#     '''Represents a table list region'''
#     _items_locator = (By.CSS_SELECTOR, "tr")

#     def __init__(self, testsetup, root, cls):
#         Page.__init__(self, testsetup, root)
#         self._item_cls = cls

#     @property
#     def items(self):
#         '''Returns a list of items represented by _item_cls'''
#         return [self._item_cls(self.testsetup, web_element)
#                 for web_element in self._root_element.find_elements(
#                         *self._items_locator)]

# class ListItem(Page):
#     '''Represents an item in the list'''
#     _item_data_locator = (By.CSS_SELECTOR, "td")

#     def click(self):
#         '''Click on the item, which will select it in the list'''
#         self._item_data[0].click()
#         self._wait_for_results_refresh()

#     @property
#     def _item_data(self):  # IGNORE:C0111
#         return [web_element
#                 for web_element in self._root_element.find_elements(
#                         *self._item_data_locator)]
