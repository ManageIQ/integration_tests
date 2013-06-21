'''
Created on March 22, 2013

@author: apagac
'''
# -*- coding: utf-8 -*-

from pages.page import Page
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.common.by import By

class TabButtons(Page):
    '''Represents the tab buttons on select screens'''
    _button_locator = (By.CSS_SELECTOR, "ul#tab > li")
    _active_tab_locator = (By.CSS_SELECTOR, "li.ui-state-active")

    def __init__(self, testsetup, locator_override=None, active_override=None, cls=TabButtonItem):
        Page.__init__(self, testsetup)
        if locator_override is not None:
            self._button_locator = locator_override
        if active_override is not None:
            self._active_tab_locator = active_override
        self._item_cls = cls

    @property
    def current_tab(self):
        '''Return the current tab page, None if _item_cls does not have a 
        _item_page dictionary
        '''
        this_tab = self._item_cls(
                self.testsetup,
                self.get_element(*self._active_tab_locator))
        return this_tab.page
    
    @property
    def tabbuttons(self):
        '''Return the list of tab buttons'''
        return [self._item_cls(self.testsetup, tabbutton_item)
                for tabbutton_item in self.selenium.find_elements(
                        *self._button_locator)]

    def tabbutton_by_name(self, target_name):
        '''Get a particular tab button by name'''
        picked = None
        for item in self.tabbuttons:
            if target_name in item.name:
                picked = item
                break
        return picked

