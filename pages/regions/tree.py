'''
Created on Mar 7, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
import re

class Tree(Page):
    '''
    classdocs
    '''

    _main_tree_item_locator = (By.CSS_SELECTOR, "table > tbody > tr > td > table > tbody")
    _root_item_locator = (By.XPATH, "tr")
    _sub_item_locator = (By.XPATH, "following-sibling::*")
    
    def __init__(self,setup,root_element,parent = None):
        Page.__init__(self, setup)
        self._root_element = root_element
        self._parent = parent
        
    @property
    def root(self):
        return self._root_element.find_element(*self._main_tree_item_locator).find_element(*self._root_item_locator)
        
    @property
    def children(self):
        return [Tree(self.testsetup, web_element, self)
                for web_element in self.root.find_elements(*self._sub_item_locator)]
    
    @property
    def name(self):
        return self.root.text.encode('utf-8')
        
    @property
    def twisty(self):
        from pages.regions.twisty import Twisty
        return Twisty(self.testsetup, self.root)
    
    @property
    def parent(self):
        return self._parent
        
    def is_displayed(self):
        return self._root_element.is_displayed()
    
    def click(self):
        return self._root_element.click()

    def find_node_by_regexp(self, regexp_str):
        # finds first node by name in the whole tree, breadth first
        regexp = re.compile(regexp_str)
        if regexp.match(self.name):
            return self
        self.twisty.expand()
        queue = self.children
        while queue:
            child = queue.pop(0)
            if regexp.match(child.name):
                return child
            else:
                child.twisty.expand()
                queue += child.children

    def find_node_by_name(self, name):
        return self.find_node_by_regexp("\A%s\Z" % re.escape(name))

    def find_node_by_substr(self, name):
        return self.find_node_by_regexp(re.escape(name))
