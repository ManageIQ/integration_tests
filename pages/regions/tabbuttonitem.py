'''
Created on March 22, 2013

@author: apagac
'''
# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By


class TabButtonItem(Page):
    '''Represents an item on a list of "tab buttons"'''
    _button_name_locator = (By.CSS_SELECTOR, "a")

    def __init__(self, testsetup, tabbutton_element):
        Page.__init__(self, testsetup, tabbutton_element)
        self._name = None

    @property
    def name(self):
        '''The tab button name'''
        if not self._name:
            self._name = self._root_element.find_element(
                    *self._button_name_locator).text
        return self._name

    @property
    def page(self):
        '''Return the page for this tab button item
        
        If the _item_page attribute exists, will return the page from that dict
        '''
        the_page = None
        if hasattr(self, "_item_page"):
            the_page = getattr(self, "_item_page")[self.name](self.testsetup)
        return the_page

    def click(self):
        '''Click the tab button'''
        self._root_element.find_element(*self._button_name_locator).click()
        self._wait_for_results_refresh()
        return self.page

