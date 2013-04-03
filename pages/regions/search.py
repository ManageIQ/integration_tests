# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By

class Search(Page):
    '''
    Search
    '''

    _text_field_locator = (By.ID, "search_text")
    _search_icon_locator = (By.ID, "searchicon")

    def search_by_name(self,name):
        self.selenium.find_element(*self._text_field_locator).send_keys(name)
        self.selenium.find_element(*self._search_icon_locator).click()     
        self._wait_for_results_refresh()
