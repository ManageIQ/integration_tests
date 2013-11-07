# -*- coding: utf-8 -*-
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
import re

class Paginator(Page):
    '''Add this region to your page with a property called paginator
    
    Example:
    @property
    def paginator(self):
        from pages.regions.paginator import Paginator
        return Paginator(self.testsetup)
        
    '''

    # TODO: so there is a paginator on the top and bottom of the region, should we randomize which one is selected
    # 130529 - dajo - had to change from #paging_div since the classes are slightly different depending on how the page
    #                   is loaded... mgmt_system all_vms click through versus services tab > VMs                   
    #Navigation
    _first_page_locator = (By.CSS_SELECTOR, "#pc_div_1 * img[alt='First']")
    _prev_locator = (By.CSS_SELECTOR, "#pc_div_1 * img[alt='Previous']")
    _next_locator = (By.CSS_SELECTOR, "#pc_div_1 * img[alt='Next']")
    _last_page_locator = (By.CSS_SELECTOR, "#pc_div_1 * img[alt='Last']")
    _per_page_locator = (By.CSS_SELECTOR, "#pc_div_1 * select[name='ppsetting']")

    #Position
    _position_text_locator = (By.CSS_SELECTOR, '#pc_div_1 > table > tbody > tr > td > table > tbody > tr > td:last-child')
    _position_regex = '(\d+)[-]?(\d+)? of (\d+)\)'
    
    # Selection
    _select_all_checkbox_locator = (By.ID, "masterToggle")

    def click_first_page(self):
        self.selenium.find_element(*self._first_page_locator).click()
        self._wait_for_results_refresh()

    def click_prev_page(self):
        self.selenium.find_element(*self._prev_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_prev_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._prev_locator).get_attribute('class')

    @property
    def is_first_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._first_page_locator).get_attribute('class')

    def click_next_page(self):
        self.selenium.find_element(*self._next_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_next_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._next_locator).get_attribute('class')

    def click_last_page(self):
        self.selenium.find_element(*self._last_page_locator).click()
        self._wait_for_results_refresh()

    @property
    def is_last_page_disabled(self):
        return 'dimmed' in self.selenium.find_element(*self._last_page_locator).get_attribute('class')

    @property
    def selected_per_page(self):
        return Select(self.selenium.find_element(*self._per_page_locator)).first_selected_option

    def set_per_page(self, value):
        Select(self.selenium.find_element(*self._per_page_locator)).select_by_value(value)
        self._wait_for_results_refresh()

    @property
    def select_all_checkbox(self):
        return self.get_element(*self._select_all_checkbox_locator)

    def select_all(self):
        if not self.select_all_checkbox.is_selected():
            self.select_all_checkbox.click()

    def deselect_all(self):
        if self.select_all_checkbox.is_selected():
            self.select_all_checkbox.click()

    @property
    def is_visible(self):
        return self.get_element(*self._first_page_locator).is_displayed()

    @property
    def position_text(self):
        return self.get_element(*self._position_text_locator)

    @property
    def _position_fields(self):
        position_value = self.position_text.text
        results = re.search(self._position_regex, position_value)
        return results.groups()

    @property
    def position_start(self):
        return self._position_fields[0]

    @property
    def position_end(self):
        return self._position_fields[1]

    @property
    def position_total(self):
        return self._position_fields[2]

class PaginatorMixin(object):
    @property
    def paginator(self):
        return Paginator(self.testsetup)
