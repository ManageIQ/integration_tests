# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By

class QuadiconItem(Page):
    '''Extend this class to create a custom QuadiconItem
    
    Add additional properties in order to customize the lookup
    
    '''
    _quadlink_locator = (By.CSS_SELECTOR, '#quadicon > div > a')
    _checkbox_locator = (By.CSS_SELECTOR, '#listcheckbox')
    _label_link_locator = (By.CSS_SELECTOR, 'tr > td > a')
    _quad_tl_locator = (By.CSS_SELECTOR, '#quadicon > div.a72')
    _quad_tr_locator = (By.CSS_SELECTOR, '#quadicon > div.b72')
    _quad_bl_locator = (By.CSS_SELECTOR, '#quadicon > div.c72')
    _quad_br_locator = (By.CSS_SELECTOR, '#quadicon > div.d72')
    
    def __init__(self, testsetup, quadicon_list_element):
        Page.__init__(self, testsetup)
        self._root_element = quadicon_list_element
    
    def click(self):
        self._root_element.find_element(*self._quadlink_locator).click()
    
    @property
    def title(self):
        return self._root_element.find_element(*self._label_link_locator).get_attribute('title')
    
    @property
    def name(self):
        return self._root_element.find_element(*self._label_link_locator).text
    
    @property
    def href_value(self):
        return self._root_element.find_element(*self._quadlink_locator).get_attribute('href')
    
    @property
    def is_selected(self):
        return self._root_element.find_element(*self._checkbox_locator).is_selected()
    
    @property
    def has_policy(self):
        # TODO: Check for policy icon
        return False
    
    def toggle_checkbox(self):
        self._root_element.find_element(*self._checkbox_locator).click()
    
    def mark_checkbox(self):
        if not self.is_selected:
            self.toggle_checkbox()
    
    def unmark_checkbox(self):
        if self.is_selected:
            self.toggle_checkbox()
