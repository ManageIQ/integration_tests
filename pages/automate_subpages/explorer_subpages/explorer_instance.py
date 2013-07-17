# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.support.select import Select
from unittestzero import Assert
from selenium.webdriver.common.keys import Keys
from time import sleep

class ExplorerInstance(Base):

    _name_instance_field = (By.ID, "cls_inst_name")
    _display_name_instance_field = (By.ID, "cls_inst_display_name")
    _description_instance_field = (By.ID, "cls_inst_description")
    _param_list_locator = (By.CSS_SELECTOR, "fieldset > table[class='style3'] > tbody")
    _param_row_zero_value = (By.CSS_SELECTOR, "fieldset > table > tbody > tr.row0 > td > input#cls_inst_value_0")
    _param_row_zero_on_entry = (By.CSS_SELECTOR, "fieldset > table > tbody > tr.row0 > td > input#cls_inst_on_entry_0")
    _param_row_one_value = (By.CSS_SELECTOR, "fieldset > table > tbody > tr.row1 > td > input#cls_inst_value_1")
    _param_row_two_value = (By.CSS_SELECTOR, "fieldset > table > tbody > tr.row0 > td > input#cls_inst_value_2")
    _param_row_three_value = (By.CSS_SELECTOR, "fieldset > table > tbody > tr.row1 > td > input#cls_inst_value_3")
    _add_system_button = (By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Add']")

    @property
    def add_system_button(self):
        return self.selenium.find_element(*self._add_system_button)

    @property
    def param_list(self):
        return ListRegion(
            self.testsetup,
            self.get_element(*self._param_list_locator),
                 ExplorerInstance.ParamItem)

    @property
    def param_row_zero_value(self):
        return  self.selenium.find_element(*self._param_row_zero_value)

    @property
    def param_row_one_value(self):
        return  self.selenium.find_element(*self._param_row_one_value)

    @property
    def param_row_two_value(self):
        return  self.selenium.find_element(*self._param_row_two_value)

    @property
    def param_row_three_value(self):
        return  self.selenium.find_element(*self._param_row_three_value)


    def fill_instance_info(self, inst_name, inst_display_name, inst_description):
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._name_instance_field).send_keys(inst_name)
        self.selenium.find_element(*self._display_name_instance_field).send_keys(inst_display_name)
        self.selenium.find_element(*self._description_instance_field).send_keys(inst_description)
        self._wait_for_visible_element(*self._add_system_button)
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)

    def fill_instance_field_row_info(self, row_number, param_value, param_on_entry, param_on_exit, param_on_error, param_collect):
        param_items = self.param_list.items
        param_items[row_number]._item_data[1].find_element_by_id('cls_inst_value_' + row_number).send_keys(param_value)
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)

    def fill_instance_field_value_only(self, field_array, value_array):
        Assert.true(len(field_array) == len(value_array))
        for i in range(0, len(field_array)):
            self._wait_for_results_refresh()
            field_array[i].click()
            field_array[i].send_keys(value_array[i])
            field_array[i].send_keys(Keys.RETURN)
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)

    def click_on_add_system_button(self):
        self.add_system_button.click()
        self._wait_for_results_refresh()
        return ExplorerInstance(self.testsetup)


    class ParamItem(ListItem):
        '''Represents a parameter in the list'''
        _columns = ["name", "value", "on_entry", "on_exit", "on_error", "collect"]

        @property
        def name(self):
            return self._item_data[0].text

        @property
        def value(self):
            return self._item_data[1].text

        @property
        def on_entry(self):
            return self._item_data[2].text

        @property
        def on_exit(self):
            return self._item_data[3].text

        @property
        def on_error(self):
            return self._item_data[4].text

        @property
        def collect(self):
            return self._item_data[5].text


