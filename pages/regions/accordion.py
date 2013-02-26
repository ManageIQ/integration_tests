# -*- coding: utf-8 -*-

'''
Created on Feb 26, 2013

@author: bcrochet
'''
from pages.page import Page
from pages.regions.accordionitem import AccordionItem
from selenium.webdriver.common.by import By

class Accordion(Page):
    '''
    Accordion
    '''

    _accordion_locator = (By.CSS_SELECTOR, "div[id^='dhxAccordionObj_'] > div")

    def __init__(self, testsetup, item_class = AccordionItem):
        '''
        Constructor
        '''
        Page.__init__(self, testsetup)
        self.item_class = item_class
    
    @property
    def accordion_items(self):
        return [self.item_class(self.testsetup, accordion_item)
                for accordion_item in self.selenium.find_elements(*self._accordion_locator)]

