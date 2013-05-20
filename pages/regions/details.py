# -*- coding: utf-8 -*-

from selenium.webdriver.common.by import By
from pages.page import Page

class Details(Page):
    _details_section_locator = (By.CSS_SELECTOR, ".modbox")

    def __init__(self, testsetup, element):
        Page.__init__(self, testsetup)
        self._root_element = element
        
    @property
    def sections(self):
        return [self.DetailsSection(self.testsetup, web_element)
                for web_element in self._root_element.find_elements(*self._details_section_locator)]
    
    def get_section(self, section_name):
        section_found = None
        for section in self.sections:
            if section_name in section.name:
                section_found = section
        return section_found
    
    def does_info_section_exist(self, section_name):
        return self.get_section(section_name) != None

    class DetailsSection(Page):
        _details_section_name_locator = (By.CSS_SELECTOR, ".modtitle")
        _details_section_data_locator = (By.CSS_SELECTOR, "tr")
        
        def __init__(self, testsetup, element):
            Page.__init__(self, testsetup)
            self._root_element = element

        @property
        def name(self):
            return self._root_element.find_element(*self._details_section_name_locator).text
        
        @property
        def items(self):
            return [self.DetailsItem(self.testsetup, web_element)
                    for web_element in self._root_element.find_elements(*self._details_section_data_locator)]
        
        def get_item(self, item_key):
            item_found = None
            for item in self.items:
                if item_key in item.key:
                    item_found = item
            return item_found
        
        def click_item(self, item_key):
            item_found = None
            for item in self.items:
                if item_key == item.key:
                    item.click()
                    break
        
        class DetailsItem(Page):
            _details_section_data_key_locator = (By.CSS_SELECTOR, "td.label")
            _details_section_data_value_locator = (By.CSS_SELECTOR, "td:not(.label)")
            
            def __init__(self, testsetup, element):
                Page.__init__(self, testsetup)
                self._root_element = element
            
            @property
            def key(self):
                return self._root_element.find_element(*self._details_section_data_key_locator).text
            
            @property
            def value(self):
                return self._root_element.find_element(*self._details_section_data_value_locator).text

            #@property
            #def has_click_through(self):
            #    return self._root_element.find_element(*self._root_element).text

            def click(self):
                self._root_element.click() 
