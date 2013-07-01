'''
Created on Mar 13, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
import re

class Twisty(Page):
    _twisty_locator = (By.CSS_SELECTOR, '.dynatree-expander:nth-of-type(1)')
    _twisty_parent_locator = (By.CSS_SELECTOR, '.dynatree-node:nth-of-type(1)')

    @property
    def _twisty_state(self):
        return 'dynatree-expanded' in self._root_element.find_element(
                *self._twisty_parent_locator).get_attribute('class')
        
    @property
    def is_closed(self):
        return not self._twisty_state
    
    @property
    def is_opened(self):
        return self._twisty_state
    
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

class LegacyTwisty(Twisty):
    _twisty_locator = (By.CSS_SELECTOR,
        "td.standartTreeImage:nth-child(1) > img")

    @property
    def _twisty_state(self):
        image_src = self._root_element.find_element(
                *self._twisty_locator).get_attribute('src')
        return re.search(r'.+/(.+)\.(png|gif)', image_src).group(1) 

    @property
    def is_closed(self):
        return "closed" in self._twisty_state
    
    @property
    def is_opened(self):
        return "open" in self._twisty_state