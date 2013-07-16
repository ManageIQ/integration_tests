# -*- coding: utf-8 -*-

from pages.base import Base
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.support.select import Select

class ExplorerMethod(Base):

    _name_method_field = (By.ID, "cls_method_name")
    _display_name_method_field = (By.ID, "cls_method_display_name")
    _location_method_choice = (By.ID, "cls_method_location")
    _method_text_area = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > div#form_div > div.CodeMirror")
    _methods_table_cell = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td[title='Methods']")
    _validate_method_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Validate method data']")
    _add_system_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")
    _flash_message = (By.CSS_SELECTOR, "div#flash_text_div_class_methods > ul#message > li#message.info")

    @property
    def method_table_cell(self):
        return self.selenium.find_element(*self._methods_table_cell)

    @property
    def method_text_area(self):
        return self.selenium.find_element(*self._method_text_area)

    @property
    def location_select(self):
        return Select(self.get_element(*self._location_method_choice))

    @property
    def validate_method_button(self):
        return self.selenium.find_element(*self._validate_method_button)

    @property
    def add_system_button(self):
        return self.selenium.find_element(*self._add_system_button)

    @property
    def flash_message_method(self):
        return self.selenium.find_element(*self._flash_message)

    def fill_method_info(self, method_name, method_display_name, location_choice, method_text):
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._name_method_field).send_keys(method_name)
        self.selenium.find_element(*self._display_name_method_field).send_keys(method_display_name)
        self.location_select.select_by_visible_text(location_choice)
        #self.selenium.find_element(*self._method_text_area).setValue(method_text)
        self._wait_for_visible_element(*self._add_system_button)
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    def click_on_method_table_cell(self, cell):
        self._wait_for_results_refresh()
        self.selenium.find_element(cell.click())
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

