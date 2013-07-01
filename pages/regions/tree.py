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
    _main_tree_item_locator = (By.CSS_SELECTOR, 'ul')
    _tree_items_locator = (By.CSS_SELECTOR, 'li')
    _tree_items_children_locator = (By.XPATH, 'ul/li')
    _tree_item_name_locator = (By.CSS_SELECTOR, 'a')

    def __init__(self,setup,root_element,parent = None):
        Page.__init__(self, setup, root_element)
        self._parent = parent

    @property
    def root(self):
        return self._root_element

    @property
    def children(self):
        child_elements = self._root_element.find_elements(
                *self._tree_items_children_locator)
        # Remaining tree item elements are children, instantiate them as
        # the same type as self to support different tree types in subclasses
        return [type(self)(self.testsetup, element, self)
                for element in child_elements]

    @property
    def twisty(self):
        from pages.regions.twisty import Twisty
        return Twisty(self.testsetup, self.root)

    @property
    def name(self):
        return self.root.find_element(
                *self._tree_item_name_locator).text.encode('utf-8')  

    @property
    def parent(self):
        return self._parent

    def is_displayed(self):
        return self.root.is_displayed()

    def click(self):
        element = self.root.click()
        self._wait_for_results_refresh()
        return element

    def find_node_by_regexp(self, regexp_str):
        # finds first node by name in the whole tree, breadth first
        regexp = re.compile(regexp_str)
        queue = [self]
        while queue:
            node = queue.pop(0)
            if regexp.match(node.name):
                return node
            else:
                node.twisty.expand()
                queue.extend(node.children)

    def find_node_by_name(self, name):
        return self.find_node_by_regexp(r"\A%s\Z" % re.escape(name))

    def find_node_by_substr(self, name):
        return self.find_node_by_regexp(re.escape(name))

class LegacyTree(Tree):
    '''Override of the tree to support DynaTree'''
    _main_tree_item_locator = (By.CSS_SELECTOR, 
            "table > tbody > tr > td > table > tbody")
    _tree_items_locator = (By.XPATH, "tr")

    @property
    def twisty(self):
        from pages.regions.twisty import LegacyTwisty
        return LegacyTwisty(self.testsetup, self.root)

    @property
    def name(self):
        return self.root.text.encode('utf-8')

    @property
    def root(self):
        # First tree item element is the root
        return self._root_element.find_element(
               *self._main_tree_item_locator).find_element(
                       *self._tree_items_locator)

    @property
    def children(self):
        tree_element =  self._root_element.find_element(
                *self._main_tree_item_locator)
        child_elements = tree_element.find_elements(*self._tree_items_locator)
        # Pop off the root element, iterate over the rest
        child_elements.pop(0)
        # Remaining tree item elements are children, instantiate them as
        # the same type as self to support different tree types in subclasses
        return [type(self)(self.testsetup, element, self)
                for element in child_elements]
