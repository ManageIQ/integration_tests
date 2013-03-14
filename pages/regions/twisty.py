'''
Created on Mar 13, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
import re

class Twisty(Page):
    _twisty_locator = (By.CSS_SELECTOR, "td.standartTreeImage:nth-child(1) > img")
    
    def __init__(self,setup,root_element):
        Page.__init__(self, setup)
        self._root_element = root_element
        
    @property
    def _twisty_state(self):
        image_src = self._root_element.find_element(*self._twisty_locator).get_attribute('src')
        return re.search('.+/(.+)\.(png|gif)',image_src).group(1) 
        
    @property
    def is_closed(self):
        return "closed" in self._twisty_state
    
    @property
    def is_opened(self):
        return "open" in self._twisty_state
    
    def click(self):
        self._root_element.find_element(*self._twisty_locator).click()
        self._wait_for_results_refresh()
    
    def expand(self):
        did_expand = False
        if self.is_closed:
            self.click()
            did_expand = True
        return did_expand
        
    def collapse(self):
        did_collapse = False
        if self.is_opened:
            self.click()
            did_collapse = True
        return did_collapse
