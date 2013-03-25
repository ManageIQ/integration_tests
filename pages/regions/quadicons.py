# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By

from pages.page import Page
from pages.regions.quadiconitem import QuadiconItem


class Quadicons(Page):
    '''Represents a Quadicon on a page
    
    To use:
    
    Create a quadicon_region property on your page
    
    Example:
    @property
    def quadicon_region(self):
        from pages.regions.quadicons import Quadicons
        return Quadicons(self.testsetup)
        
    To extend the items returned, create a subclass of QuadiconItem, and add any additional properties
    Quadicons(self.testsetup, MyQuadiconItem)
    
    '''
    _quadicons_locator = (By.CSS_SELECTOR, "#records_div > table > tbody > tr > td > div")
    
    def __init__(self, setup, item_class = QuadiconItem):
        super(Quadicons, self).__init__(setup)
        self.item_class = item_class

    @property
    def quadicons(self):
        return [self.item_class(self.testsetup, quadicon_list_item)
                for quadicon_list_item in self.selenium.find_elements(*self._quadicons_locator)]

    def mark_icon_checkbox(self, vm_names):
        for name in vm_names:
            tile = self.get_quadicon_by_title(name)
            tile.mark_checkbox()

    def get_quadicon_by_title(self, title):
        for tile in self.quadicons:
            if tile.title == title:
                return tile

    def does_quadicon_exist(self, title):
        found = False
        for tile in self.quadicons:
            if tile.title == title:
                found = 1
                break
        return found
