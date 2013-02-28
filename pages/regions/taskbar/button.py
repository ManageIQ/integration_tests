'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.page import Page

class Button(Page):
    def __init__(self,setup,*element):
        Page.__init__(self,setup)
        self._root_element = self.selenium.find_element(*element)
            
    @property
    def exists(self):
        return self._root_element.is_displayed
    