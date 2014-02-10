'''Created on July 25, 2013

@author: shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import random
import time

class Catalogs(Base):
    '''Service -- Catalog page'''
    _page_title = 'CloudForms Management Engine: Catalogs'
    _configuration_button_locator = (
        By.CSS_SELECTOR,
        "div.dhx_toolbar_btn[title='Configuration']")
    _add_catalog_button_locator = (
        By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Add a New Catalog']")
    _edit_catalog_button_locator = (
        By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Edit this Item']")
    _del_catalog_button_locator = (
        By.CSS_SELECTOR, 
        "table.buttons_cont tr[title='Remove this Item from the VMDB']")
    _name_list_locator = (
        By.CSS_SELECTOR,
        "div#list_grid > div#xhdr > table > tbody > tr >td ")
    _name_field = (By.CSS_SELECTOR, "input[name='name']")
    _desc_field = (By.CSS_SELECTOR, "input[name='description']")
    _add_button = (By.CSS_SELECTOR, "img[title='Add']")
    _save_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
     
    @property
    def accordion(self):
        '''accordion'''
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)
         
    def add_new_catalog(self):
        '''Click Configuration and then add catalog btn'''
        self.click_on_catalog("All Catalogs")
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._add_catalog_button_locator).click()
        return Catalogs(self.testsetup)
    
    def edit_catalog(self, catalog_name):
        '''Go to edit catalog page'''
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._edit_catalog_button_locator).click()
        self.get_element(*self._name_field).send_keys(catalog_name)
        self._wait_for_visible_element(*self._save_button)
        self.get_element(*self._save_button).click()
        self._wait_for_results_refresh()
        return Catalogs(self.testsetup)
    
    def delete_catalog(self):
        '''Delete catalog'''
        self.get_element(*self._configuration_button_locator).click()
        self.get_element(*self._del_catalog_button_locator).click()
        self.handle_popup()
        self._wait_for_results_refresh()
        return Catalogs(self.testsetup)
    
    def click_on_catalog(self, catalog_name):
        '''Click on catalog to edit or delete'''
        self.accordion.current_content.find_node_by_name(catalog_name).click()
        self._wait_for_results_refresh()
        return Catalogs(self.testsetup)
         
    def fill_basic_info_tab(self, name, descr):
        '''Fill catalog create form'''
        self.get_element(*self._name_field).send_keys(name)
        self.get_element(*self._desc_field).send_keys(descr)
        self._wait_for_visible_element(*self._add_button)
        #time.sleep(2)
        self.get_element(*self._add_button).click()
        self._wait_for_results_refresh()
        return Catalogs(self.testsetup)