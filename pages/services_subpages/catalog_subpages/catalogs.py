from pages.base import Base
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.taggable import Taggable
from selenium.webdriver.common.action_chains import ActionChains


class Catalogs(Base):
     _page_title = 'CloudForms Management Engine: Catalogs'
     _configuration_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Configuration']")
     _add_catalog_button_locator = (By.CSS_SELECTOR, "table.buttons_cont tr[title='Add a New Catalog']")
         
     @property
     def configuration_button(self):
         return self.selenium.find_element(*self._configuration_button_locator)

     @property
     def add_catalog_button(self):
         return self.selenium.find_element(*self._add_catalog_button_locator)
        
     def add_new_catalog(self):
        ActionChains(self.selenium).click(self.configuration_button).click(self.add_catalog_button).perform()
        return Catalogs.NewCatalog(self.testsetup)
        
     class NewCatalog(Base):
         _name_field = (By.CSS_SELECTOR, "input[name='name']")
         _desc_field = (By.CSS_SELECTOR, "input[name='description']")
         _add_button = (By.CSS_SELECTOR, "img[title='Add']")
         
         def fill_name(self, name):
            return self.selenium.find_element(*self._name_field).send_keys(name)
        
         def fill_desc(self, desc):
            return self.selenium.find_element(*self._desc_field).send_keys(desc)
        
         def save(self):
            # when editing an existing role, wait until "save" button shows up
            # after ajax validation
            self._wait_for_visible_element(*self._add_button)
            self.selenium.find_element(*self._add_button).click()
            self._wait_for_results_refresh()
            return Catalogs(self.testsetup)
