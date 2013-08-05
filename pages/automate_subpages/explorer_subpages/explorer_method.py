# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from pages.regions.list import ListRegion, ListItem

class ExplorerMethod(Base):

    '''Class for Automate -> Explorer, Class component'''
    _name_method_field = (By.ID, "cls_method_name")
    _display_name_method_field = (By.ID, "cls_method_display_name")
    _location_method_choice = (By.ID, "cls_method_location")
    _configuration_button = (By.CSS_SELECTOR,
                "div.dhx_toolbar_btn[title='Configuration']")
    _method_code_mirror = (By.CSS_SELECTOR, \
        "fieldset > table > tbody > tr > td > div#form_div > div.CodeMirror")
    _method_text_area = (By.CSS_SELECTOR, \
        "fieldset > table > tbody > tr > td \
         > div#form_div > div.CodeMirror > div > textarea")
    _methods_table_cell = (By.CSS_SELECTOR, "fieldset \
         > table > tbody > tr > td[title='Methods']")
    _validate_method_button = (By.CSS_SELECTOR, \
        "ul#form_buttons > li > img[title='Validate method data']")
    _add_system_button = (By.CSS_SELECTOR, \
        "ul#form_buttons > li > img[title='Add']")
    _flash_message = (By.CSS_SELECTOR, \
        "div#flash_text_div_class_methods > ul#message > li#message.info")
    _method_list_table = (By.CSS_SELECTOR, \
        "div#cls_methods_grid_div > div.objbox > table.obj > tbody")
    _edit_method_button_locator = (By.CSS_SELECTOR,
                "table.buttons_cont tr[title='Select a single Method to edit']")

    @property
    def method_table_cell(self):
        '''Cell in the method table'''
        return self.selenium.find_element(*self._methods_table_cell)

    @property
    def method_text_area(self):
        '''Code Mirror'''
        return self.selenium.find_element(*self._method_text_area)

    @property
    def location_select(self):
        '''Location of method'''
        return Select(self.get_element(*self._location_method_choice))

    @property
    def validate_method_button(self):
        '''Validate method button'''
        return self.selenium.find_element(*self._validate_method_button)

    @property
    def add_system_button(self):
        '''Add button'''
        return self.selenium.find_element(*self._add_system_button)

    @property
    def edit_method_button(self):
        '''Configuration -> Edit Selected Method''' 
        return self.selenium.find_element(*self._edit_method_button_locator)

    @property
    def flash_message_method(self):
        '''Flash message'''
        return self.selenium.find_element(*self._flash_message)

    @property
    def configuration_button(self):
        '''Configuration button'''
        return self.selenium.find_element(*self._configuration_button)

    @property
    def method_list(self):
        '''Returns list of methods in the table'''
        return ListRegion(
            self.testsetup,
            self.get_element(*self._method_list_table),
                 ExplorerMethod.MethodItem)

    def fill_method_info(self, method_name, method_display_name, \
        location_choice, method_text):
        '''Fills field info to add a new method'''
        self._wait_for_results_refresh()
        self.selenium.find_element(\
            *self._name_method_field).send_keys(method_name)
        self.selenium.find_element(\
            *self._display_name_method_field).send_keys(method_display_name)
        self.location_select.select_by_visible_text(location_choice)
        self.selenium.find_element(*self._method_code_mirror).click()
        self.selenium.find_element(\
            *self._method_text_area).send_keys(method_text)
        self._wait_for_visible_element(*self._add_system_button)
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    def select_edit_method(self, item_name):
        '''Selects a method and then clicks 
        Configuration -> Edit selected method'''
        method_items = self.method_list.items
        selected_item = None
        for i in range(1, len(method_items)):
            if method_items[i].name == item_name:
                selected_item = method_items[i]
                selected_item.checkbox.find_element_by_tag_name('img').click()

        ActionChains(self.selenium).click(self.configuration_button)\
            .click(self.edit_method_button).perform()
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    def click_on_add_system_button(self):
        '''Clicks on the Add button'''
        self.add_system_button.click()
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    def click_on_validate_method_button(self):
        '''Clicks on the Validate button'''
        self.validate_method_button.click()
        self._wait_for_results_refresh()
        return ExplorerMethod(self.testsetup)

    class MethodItem(ListItem):
        '''Represents a method in the list'''
        _columns = ["checkbox", "icon", "name"]

        @property
        def checkbox(self):
            '''Checkbox'''
            return self._item_data[0]

        @property
        def icon(self):
            '''Method icon'''
            pass

        @property
        def name(self):
            '''Method name'''
            return self._item_data[2].text

