# -*- coding: utf-8 -*-

from pages.base import Base
from pages.page import Page
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select

class ExplorerSchema(Base):

    _add_new_field_schema_button = (By.CSS_SELECTOR, "fieldset > table > tbody > tr[title='Click to add a new field']")
    _add_this_entry_checkmark = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > a[title='Add this entry']")
    _schema_name_field = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > input#field_name")
    _schema_type_select = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > div#field_aetype_id > div[class='dhx_combo_box'] > img[class='dhx_combo_img']")
    _schema_data_type_select = (By.CSS_SELECTOR, "fieldset > table > tbody > tr > td > div#field_datatype_id > div[class='dhx_combo_box'] > img[class='dhx_combo_img']")
    _schema_type_attribute = (By.CSS_SELECTOR, 'div.dhx_combo_list > div > img[src="/images/icons/new/16_ae_attribute.png"]')
    _schema_type_method = (By.CSS_SELECTOR, 'div.dhx_combo_list > div > img[src="/images/icons/new/16_ae_method.png"]')
    _schema_type_relationship = (By.CSS_SELECTOR, 'div.dhx_combo_list > div > img[src="/images/icons/new/16_ae_relationship.png"]')
    _schema_data_type_string = (By.CSS_SELECTOR, 'div.dhx_combo_list > div > img[src="/images/icons/new/string.png"]')
    _schema_save_button = (By.CSS_SELECTOR, "div#form_buttons_div > table > tbody > tr > td > div > ul > li img[alt='Save Changes']")


    @property
    def schema_type_select(self):
       return self.selenium.find_element(*self._schema_type_select)

    @property
    def schema_data_type_select(self):
       return self.selenium.find_element(*self._schema_data_type_select)

    @property
    def schema_save_button(self):
       return self.selenium.find_element(*self._schema_save_button)

    def schema_type_attribute_button(self):
       return self.selenium.find_element(*self._schema_type_attribute)

    def schema_type_method_button(self):
       return self.selenium.find_element(*self._schema_type_method)

    def schema_type_relationship_button(self):
       return self.selenium.find_element(*self._schema_type_relationship)

    def schema_data_type_string_button(self):
       return self.selenium.find_element(*self._schema_data_type_string)

    def type_select(self, name_string):
       return{
          'Attribute'    : self.schema_type_attribute_button(),
          'Method'       : self.schema_type_method_button(),
          'Relationship' : self.schema_type_relationship_button()
          # 'State'
          # 'Assertion'
       }[name_string]

    def data_type_select(self, name_string):
       return{
          'String' : self.schema_data_type_string_button()
          # 'Symbol'
          # 'Integer'
       }[name_string]

    def add_new_field(self, param_name, param_type, param_data_type):
       self._wait_for_results_refresh()
       self.selenium.find_element(*self._add_new_field_schema_button).click()
       self._wait_for_results_refresh()
       self.selenium.find_element(*self._schema_name_field).send_keys(param_name)
       ActionChains(self.selenium).click(self.schema_type_select).click(self.type_select(param_type)).perform()
       self._wait_for_results_refresh()
       ActionChains(self.selenium).click(self.schema_data_type_select).click(self.data_type_select(param_data_type)).perform()
       self._wait_for_results_refresh()
       self.selenium.find_element(*self._add_this_entry_checkmark).click()
       self._wait_for_results_refresh()
       return ExplorerSchema(self.testsetup)


