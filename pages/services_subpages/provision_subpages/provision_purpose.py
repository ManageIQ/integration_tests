'''
Created on May 2, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class ProvisionPurpose(Base):
    '''Models the Purpose subpage in the Provision wizard'''
    _tag_tree_locator = (By.CSS_SELECTOR, "div#all_tags_treebox")

    @property
    def tag_tree(self):
        from pages.regions.tree import Tree
        the_tree = Tree(self.testsetup, *self._tag_tree_locator)
        the_tree._main_tree_item_locator = self._tag_tree_locator
        return the_tree
