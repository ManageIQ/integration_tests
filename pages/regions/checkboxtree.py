'''
Created on Apr 11, 2013

@author: jprovazn
'''

# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from pages.regions.tree import Tree
from pages.regions.tree import LegacyTree


class Checkbox(object):
    _checkbox_locator = (By.CSS_SELECTOR, ".dynatree-checkbox")
    _checkbox_parent_locator = (
            By.CSS_SELECTOR, ".dynatree-node:nth-of-type(1)")

    @property
    def _checkbox_state(self):
        return "dynatree-selected" in self._cb_parent.get_attribute("class")

    def check(self):
        if self.is_checked:
            return True
        return self._checkbox.click()

    def uncheck(self):
        if self.is_unchecked:
            return True
        return self._checkbox.click()

    @property
    def is_unchecked(self):
        return not self._checkbox_state

    @property
    def is_checked(self):
        return self._checkbox_state

    @property
    def _cb_parent(self):
        return self._root_element.find_element(*self._checkbox_parent_locator)

    @property
    def _checkbox(self):
        return self._root_element.find_element(*self._checkbox_locator)

class LegacyCheckbox(Checkbox):
    _checkbox_locator = (By.CSS_SELECTOR, "tr > td:nth-child(2) > img")

    @property
    def _checkbox_state(self):
        return "iconCheckAll" in self._checkbox_img

    @property
    def _checkbox_img(self):
        return self._checkbox.get_attribute('src')

class CheckboxTree(Tree, Checkbox):
    '''
    Checkbox tree with parent-child nodes
    '''

class LegacyCheckboxTree(LegacyTree, LegacyCheckbox):
    '''
    Checkbox dynatree with parent-child nodes
    '''
