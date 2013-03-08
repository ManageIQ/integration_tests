'''
Created on Mar 7, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By

class Tree(Page):
    '''
    classdocs
    '''

    _main_tree_item_locator = (By.CSS_SELECTOR, "table > tbody > tr > td > table > tbody")
    _root_item_locator = (By.XPATH, "tr")
    _sub_item_locator = (By.XPATH, "following-sibling::*")
    
    def __init__(self,setup,root_element):
        Page.__init__(self, setup)
        self._root_element = root_element
        
    @property
    def root(self):
        return self._root_element.find_element(*self._main_tree_item_locator).find_element(*self._root_item_locator)
        
    @property
    def children(self):
        return [Tree(self.testsetup, web_element)
                for web_element in self.root.find_elements(*self._sub_item_locator)]
    
    @property
    def name(self):
        return self.root.text.encode('utf-8')
        
    def is_displayed(self):
        return self._root_element.is_displayed()
    