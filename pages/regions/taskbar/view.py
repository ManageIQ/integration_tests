'''
Created on Feb 28, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.regions.taskbar.button import Button
from selenium.webdriver.common.by import By

class ViewButtons(Button):
    _view_buttons_locator = (By.CSS_SELECTOR, "#view_buttons_div > #view_tb")
    _grid_view_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Grid View']")
    _tile_view_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Tile View']")
    _list_view_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='List View']")
    _download_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Download']")
    _download_arrow_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_arw[title='Download']")
    
    def __init__(self,setup):
        Button.__init__(self, setup, *self._view_buttons_locator)

    @property
    def grid_view_button(self):
        return self._root_element.find_element(*self._grid_view_button_locator)
    
    @property
    def tile_view_button(self):
        return self._root_element.find_element(*self._tile_view_button_locator)
    
    @property
    def list_view_button(self):
        return self._root_element.find_element(*self._list_view_button_locator)
    
    @property
    def download_button(self):
        return self._root_element.find_element(*self._download_button_locator)
    
    @property
    def is_grid_view(self):
        return self._is_current_view(self.grid_view_button)
    
    @property
    def is_tile_view(self):
        return self._is_current_view(self.tile_view_button)
        
    @property
    def is_list_view(self):
        return self._is_current_view(self.list_view_button)

    def _switch_to_view(self, button):
        button.click()
        self._wait_for_results_refresh()
    
    def change_to_grid_view(self):
        self._switch_to_view(self.grid_view_button)
        
    def change_to_tile_view(self):
        self._switch_to_view(self.tile_view_button)
    
    def change_to_list_view(self):
        self._switch_to_view(self.list_view_button)
        
    def _is_current_view(self, button):
        return "dis" in button.get_attribute('class')
    
    
        
