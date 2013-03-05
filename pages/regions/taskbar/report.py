'''
Created on Mar 5, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class ReportButtons(Button):
    '''
    classdocs
    '''

    _report_buttons_locator = (By.CSS_SELECTOR, "#report_buttons_div")
    _report_refresh_button_locator = (By.CSS_SELECTOR, "li > a[title='Reload selected Reports'] > img")
    _report_delete_button_locator = (By.CSS_SELECTOR, "li > img[title='Select one or more Saved Reports to delete']")
    
    def __init__(self,setup):
        Button.__init__(self, setup, self._report_buttons_locator)
        # TODO: Add more initialization here
        
    @property
    def refresh_button(self):
        return self._root_element.find_element(*self._report_reload_button_locator)
    
    @property
    def delete_button(self):
        return self._root_element.find_element(*self._report_delete_button_locator)
    
    def delete(self):
        self.delete_button.click()
        self._wait_for_results_refresh()
        
    def refresh(self):
        self.refresh_button.click()
        self._wait_for_results_refresh()