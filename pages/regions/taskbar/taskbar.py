'''
Created on Feb 26, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.page import Page
from selenium.webdriver.common.by import By
from pages.regions.taskbar.history import HistoryButtons
from pages.regions.taskbar.view import ViewButtons
from pages.regions.taskbar.center import CenterButtons

class Taskbar(Page):
    '''
    Taskbar
    '''
    
    _taskbar_locator = (By.CSS_SELECTOR, "div#taskbar_div")

    def __init__(self,setup):
        Page.__init__(self, setup)
        
    @property
    def history_buttons(self):
        return HistoryButtons(self.testsetup)
    
    @property
    def center_buttons(self):
        return CenterButtons(self.testsetup)
    
    @property
    def view_buttons(self):
        return ViewButtons(self.testsetup)
    