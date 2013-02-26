'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class CenterButtons(Button):
    '''
    classdocs
    '''

    _center_buttons_locator = (By.CSS_SELECTOR, "#center_buttons_div")
    
    def __init__(self,setup):
        Button.__init__(self, setup, *self._center_buttons_locator)
        
        