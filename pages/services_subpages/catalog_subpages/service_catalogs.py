from pages.page import Page
from pages.base import Base
import random
from pages.regions.checkboxtree import CheckboxTree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.regions.taggable import Taggable
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.list import ListRegion, ListItem
from pages.services_subpages.catalog_subpages.order_service import OrderService


class ServiceCatalogs(Base):
     _order_button = (By.CSS_SELECTOR, "img[title='Order this Service']")
     _submit_button = (By.CSS_SELECTOR, "img[title='Submit']")
     
     @property
     def accordion(self):
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import TreeAccordionItem
        return Accordion(self.testsetup,TreeAccordionItem)

     def click_on_catalog_in_service_tree(self,_catalog_name):
        self.accordion.current_content.find_node_by_name(_catalog_name).click()
        self._wait_for_results_refresh()
        return ServiceCatalogs(self.testsetup)
    
     def select_catalog_item(self,catalog_name):
          number_of_templates = len(OrderService(self).order_catalog_list.items)
          print number_of_templates
          catalog_item = None
          '''First item in list is empty so skipped'''
          for item in OrderService(self).order_catalog_list.items[1:]:
              if item.name == catalog_name:
                  catalog_item = item
                  print item.name
                  catalog_item.click()
          self._wait_for_results_refresh()
          self.selenium.find_element(*self._order_button).click()
          self._wait_for_results_refresh()
          self.selenium.find_element(*self._submit_button).click()
          self._wait_for_results_refresh()
    