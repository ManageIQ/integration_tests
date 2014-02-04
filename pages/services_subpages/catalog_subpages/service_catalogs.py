''' Created on July 25th, 2013

@author: Shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from pages.services_subpages.catalog_subpages.order_service import OrderService
import time


class ServiceCatalogs(Base):
    '''Service -- Service catalog page'''
    _order_button = (By.CSS_SELECTOR, "img[title='Order this Service']")
    _submit_button = (By.CSS_SELECTOR, "img[title='Submit']")
    _dialog_service_name_field =  (
        By.CSS_SELECTOR, "tr > td[title='_ele_desc'] input#service_name")
     
    @property
    def accordion(self):
        '''accordion'''
        from pages.regions.accordion import Accordion
        from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
        return Accordion(self.testsetup, LegacyTreeAccordionItem)
    
    def select_catalog_in_service_tree(self, _catalog_name):
        '''Select catalog'''
        self.accordion.current_content.find_node_by_name(_catalog_name).click()
        self._wait_for_results_refresh()
        return ServiceCatalogs(self.testsetup)
    
    def is_catalog_present(self, _catalog_name):
        '''Select catalog'''
        if(self.accordion.current_content.find_node_by_name(_catalog_name)):
            self._wait_for_results_refresh()
            return True
        else:
            return False
        
    def is_catalog_item_present(self, _catalog_item):
        '''Select catalog'''
        if(self.accordion.current_content.find_node_by_name(_catalog_item)):
            self._wait_for_results_refresh()
            return True
        else:
            return False
        
    def click_order(self):
        '''Click Order Button'''
        self._wait_for_results_refresh()
        self.get_element(*self._order_button).click()
        self._wait_for_results_refresh()
        
    def click_submit(self):
        '''Click Submit'''
        self.get_element(*self._submit_button).click()
        self._wait_for_results_refresh()
        
    def service_name_field(self):
        '''Service name field'''
        return self.get_element(*self._dialog_service_name_field)
    
    def select_catalog_item(self, catalog_item_name, service_name):
        #number_of_templates = len(OrderService(self).order_catalog_list.items)
        #catalog_item = None
        '''First item in list is empty so skipped'''
        for item in OrderService(self).order_catalog_list.items[1:]:
            if item.name == catalog_item_name:
                item.click()
        self.click_order()
        #time.sleep(5)
        self._wait_for_visible_element(*self._dialog_service_name_field)
        #self._wait_for_results_refresh()
        self.service_name_field().clear()
        self.service_name_field().send_keys(service_name)
        self.click_submit()
        self._wait_for_results_refresh()
        from pages.services import Services
        return Services.Requests(self.testsetup)    