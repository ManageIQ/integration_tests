from pages.page import Page
from pages.base import Base
import random
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.taggable import Taggable
from selenium.webdriver.common.action_chains import ActionChains


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
        
        def create_service_dialog(self, label, _desc):
             self.selenium.find_element(*self._label_field).send_keys(label)
             self.selenium.find_element(*self._desc_field).send_keys(_desc)
             self.selenium.find_element(*self._submit_button_checkbox).click()
             self.selenium.find_element(*self._cancel_button_checkbox).click()
             self._wait_for_visible_element(*self._add_button)
             self.selenium.find_element(*self._add_button).click()
             self._wait_for_results_refresh()
             return Customization(self.testsetup)
            