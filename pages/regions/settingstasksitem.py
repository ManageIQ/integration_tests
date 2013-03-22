# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By

class STItem(Page):

    #_button_active_locator = (By.CSS_SELECTOR, "#active")
    #_button_inactive_locator = (By.CSS_SELECTOR, "#inactive")

    def __init__(self, testsetup, st_element):
        Page.__init__(self, testsetup)
        self._root_element = st_element

    """
    @property
    def active_name(self):
        return self._root_element.find_element(*self._button_active_locator).text

    @property
    def inactive_name(self):
        return self._root_element.find_element(*self._button_inactive_locator).text
    """

    @property
    def name(self):
        return self._root_element.text

    def click(self):
        self._root_element.click()
        self._wait_for_results_refresh()
