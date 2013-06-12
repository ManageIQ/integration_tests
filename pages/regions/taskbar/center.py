'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class CenterButtons(Button):
    '''
    classdocs
    '''

    _center_buttons_locator = (By.CSS_SELECTOR, "#center_buttons_div > #center_tb")
    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration'] > div")
    _policy_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Policy'] > div")
    _lifecycle_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Lifecycle'] > div")
    _power_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Power'] > div")
    _monitoring_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Monitoring'] > div")

    def __init__(self, setup):
        Button.__init__(self, setup, *self._center_buttons_locator)

    @property
    def configuration_button(self):
        return self._root_element.find_element(*self._configuration_button_locator)

    @property
    def lifecycle_button(self):
        return self._root_element.find_element(*self._lifecycle_button_locator)

    @property
    def monitoring_button(self):
        return self._root_element.find_element(*self._monitoring_button_locator)
