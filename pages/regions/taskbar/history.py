'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class HistoryButtons(Button):
    _history_buttons_locator = (By.CSS_SELECTOR, "#history_buttons_div > #history_tb")
    _history_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='History']")
    _history_arrow_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_arw[title='History']")
    _refresh_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Reload current display']")
    
    def __init__(self,setup):
        Button.__init__(self,setup,*self._history_buttons_locator)
    
    @property
    def history_button(self):
        return self._root_element.find_element(*self._history_button_locator)
    
    @property
    def history_arrow_button(self):
        return self._root_element.find_element(*self._history_arrow_button_locator)
    
    @property
    def refresh_button(self):
        return self._root_element.find_element(*self._refresh_button_locator)

