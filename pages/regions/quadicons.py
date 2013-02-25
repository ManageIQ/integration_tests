# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By

from pages.page import Page
from pages.regions.quadiconitem import QuadiconItem


class Quadicons(Page):
    _quadicons_locator = (By.CSS_SELECTOR, "#records_div > table > tbody > tr > td > div")
    
    def __init__(self, setup, item_class = QuadiconItem):
        super(Quadicons, self).__init__(setup)
        self.item_class = item_class

    @property
    def quadicons(self):
        return [self.item_class(self.testsetup, quadicon_list_item)
                for quadicon_list_item in self.selenium.find_elements(*self._quadicons_locator)]

    def get_quadicon_by_title(self, title):
        for tile in self.quadicons:
            if tile.find_elements_by_css_selector('a')[1].get_attribute('title') == title:
                return tile

