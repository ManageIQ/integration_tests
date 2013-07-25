from pages.page import Page
from pages.base import Base
import random
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.taggable import Taggable
from selenium.webdriver.common.action_chains import ActionChains
import time


class Customization(Base):
    _page_title = 'CloudForms Management Engine: Automate'
    _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
    _add_dialog_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a new Dialog']")
     
     
    @property
    def configuration_button(self):
        return self.selenium.find_element(*self._configuration_button_locator)

    @property
    def _add_dialog_button(self):
        return self.selenium.find_element(*self._add_dialog_button_locator)
        
    def add_new_service_dialog(self):
       ActionChains(self.selenium).click(self.configuration_button).click(self._add_dialog_button).perform()
       return Customization.NewServiceDialog(self.testsetup)
        
        
    class NewServiceDialog(Base):
        _label_field = (By.CSS_SELECTOR, "input[name='label']")
        _desc_field = (By.CSS_SELECTOR, "input[name='description']")
        _submit_button_checkbox = (By.CSS_SELECTOR, "input[name='chkbx_submit']")
        _cancel_button_checkbox = (By.CSS_SELECTOR, "input[name='chkbx_cancel']")
        _add_button = (By.CSS_SELECTOR, "img[title='Add']")
        _plus_button = (By.CSS_SELECTOR, "div.dhx_toolbar_arw[title='Add']")
        _add_tab_button= (By.CSS_SELECTOR, "tr.tr_btn[title='Add a New Tab to this Dialog']")
        _tab_label = (By.CSS_SELECTOR, "input[id='tab_label']")
        _tab_desc = (By.CSS_SELECTOR, "input[id='tab_description']")
        _add_box_button= (By.CSS_SELECTOR, "tr.tr_btn[title='Add a New Box to this Tab']")
        _box_label = (By.CSS_SELECTOR, "input[id='group_label']")
        _box_desc = (By.CSS_SELECTOR, "input[id='group_description']")
        _add_element_button = (By.CSS_SELECTOR, "tr.tr_btn[title='Add a New Element to this Box']")
        _ele_label = (By.CSS_SELECTOR, "input[id='field_label']")
        _ele_name = (By.CSS_SELECTOR, "input[id='field_name']")
        _ele_desc = (By.CSS_SELECTOR, "input[id='field_description']")
        _choose_type = (By.CSS_SELECTOR, "select#field_typ")
        
        def random_string(self):
             rand_string = ""
             letters = 'abcdefghijklmnopqrstuvwxyz'
             for i in xrange(8):
                 rand_string += random.choice(letters)
             return rand_string    
        
        def create_service_dialog(self,servicedialogname):
             rand_string =  self.random_string()
             self.selenium.find_element(*self._label_field).send_keys(servicedialogname)
             self.selenium.find_element(*self._desc_field).send_keys(rand_string+"_desc")
             self.selenium.find_element(*self._submit_button_checkbox).click()
             self.selenium.find_element(*self._cancel_button_checkbox).click()
             self.add_tab_to_dialog(rand_string+"_tab_label",rand_string+"_tab_desc")
             self.add_box_to_dialog(rand_string+"_box_label",rand_string+"_box_desc")
             time.sleep(5)
             self.add_element_to_dialog(rand_string+"_ele_label",rand_string+"_ele_name",rand_string+"_ele_desc")
             self._wait_for_visible_element(*self._add_button)
             self.selenium.find_element(*self._add_button).click()
             self._wait_for_results_refresh()
             return Customization(self.testsetup)
            
            
        def add_tab_to_dialog(self,_tab_label,_tab_desc):
             time.sleep(3)
             self.selenium.find_element(*self._plus_button).click()
             self._wait_for_results_refresh()
             time.sleep(3)
             self.selenium.find_element(*self._add_tab_button).click()
             self._wait_for_results_refresh()
             self.selenium.find_element(*self._tab_label).send_keys(_tab_label)
             self.selenium.find_element(*self._tab_desc).send_keys(_tab_desc)
             return self
         
        def add_box_to_dialog(self,box_label,box_desc):
             time.sleep(3)
             self.selenium.find_element(*self._plus_button).click()
             self._wait_for_results_refresh()
             time.sleep(5)
             self.selenium.find_element(*self._add_box_button).click()
             self._wait_for_results_refresh()
             #time.sleep(5)
             self.selenium.find_element(*self._box_label).send_keys(box_label)
             self.selenium.find_element(*self._box_desc).send_keys(box_desc)
             return self
         
        def add_element_to_dialog(self,ele_label,ele_name,ele_desc):
             self.selenium.find_element(*self._plus_button).click()
             self._wait_for_results_refresh()
             self.selenium.find_element(*self._add_element_button).click()
             self._wait_for_results_refresh()
             #time.sleep(5)
             self.selenium.find_element(*self._ele_label).send_keys(ele_label)
             self.selenium.find_element(*self._ele_name).send_keys(ele_name)
             self.selenium.find_element(*self._ele_desc).send_keys(ele_desc)
             self.select_dropdown("Check Box",*self._choose_type)
             return self