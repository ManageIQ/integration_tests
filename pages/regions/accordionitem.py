# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By

class AccordionItem(Page):
    _item_label_locator = (By.CSS_SELECTOR, ".dhx_acc_item_label")
    _item_name_locator = (By.CSS_SELECTOR, ".dhx_acc_item_label > span")
    _item_content_locator = (By.CSS_SELECTOR, "div[ida='dhxMainCont']")
    
    def __init__(self, testsetup, accordion_element):
        Page.__init__(self, testsetup)
        self._root_element = accordion_element
    
    @property
    def name(self):
        return self._root_element.find_element(*self._item_name_locator).text

    @property
    def content(self):
        return self._root_element.find_element(*self._item_content_locator)
    
    def click(self):
        name = self.name
        self._root_element.find_element(*self._item_label_locator).click()
        self._wait_for_results_refresh()
        
        # Check name and return proper region
