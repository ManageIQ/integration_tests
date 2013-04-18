# -*- coding: utf-8 -*-

from pages.page import Page
from pages.regions.settingstasksitem import STItem
from selenium.webdriver.common.by import By

class SettingsTasks(Page):

    _button_locator = (By.CSS_SELECTOR, "ul#tab > li > a")

    def __init__(self, testsetup, item_class = STItem):
        Page.__init__(self, testsetup)
        self.item_class = item_class

    @property
    def ST_items(self):
        items = []

        for item in self.selenium.find_elements(*self._button_locator):
            items.append(self.item_class(self.testsetup, item))

        return items

    def ST_item_by_name(self, target_name):
        picked = None

        for item in self.ST_items:
            if target_name in item.name:
                picked = item
                break
        return picked
