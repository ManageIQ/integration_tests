# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By


class TabButtonItem(Page):

    _button_name_locator = (By.CSS_SELECTOR, "a")

    def __init__(self, testsetup, tabbutton_element):
        Page.__init__(self, testsetup)
        self._root_element = tabbutton_element

    @property
    def name(self):
        return self._root_element.find_element(*self._button_name_locator).text

    def click(self):
        self._root_element.find_element(*self._button_name_locator).click()
        self._wait_for_results_refresh()

