# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By


class TabButtons(Page):
    _button_locator = (By.CSS_SELECTOR, "ul#tab > li")

    def __init__(self, testsetup, locator_override):
        Page.__init__(self, testsetup)
        if locator_override:
            self._button_locator = locator_override

    
    @property
    def tabbuttons(self):
        from pages.regions.tabbuttonitem import TabButtonItem
        return [TabButtonItem(self.testsetup, tabbutton_item)
                for tabbutton_item in self.selenium.find_elements(*self._button_locator)]

    def tabbutton_by_name(self, target_name):
        picked = None
        for item in self.tabbuttons:
            if target_name in item.name:
                picked = item
                break
        return picked

