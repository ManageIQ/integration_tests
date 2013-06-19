'''
Created on Apr 11, 2013

@author: jprovazn
'''

# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
from pages.regions.tree import Tree


class Checkbox(object):

    _checkbox_locator = (By.CSS_SELECTOR, "tr > td:nth-child(2) > img")

    def check(self):
        if self.is_checked:
            return True
        return self._checkbox.click()

    def uncheck(self):
        if not self.is_checked:
            return True
        return self._checkbox.click()

    @property
    def is_checked(self):
        return "iconCheckAll" in self._checkbox_img

    @property
    def _checkbox(self):
        return self._root_element.find_element(*self._checkbox_locator)

    @property
    def _checkbox_img(self):
        return self._checkbox.get_attribute('src')


class CheckboxTree(Tree, Checkbox):
    '''
    Checkbox tree with parent-child nodes
    '''
