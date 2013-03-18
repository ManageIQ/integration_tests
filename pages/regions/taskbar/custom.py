'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class CustomButtons(Button):
    '''
    classdocs
    '''

    _custom_buttons_locator = (By.CSS_SELECTOR, "#custom_buttons_div > #custom_tb")
    
    def __init__(self,setup):
        Button.__init__(self, setup, self._custom_buttons_locator)
        
