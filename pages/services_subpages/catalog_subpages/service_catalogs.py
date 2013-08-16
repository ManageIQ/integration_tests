''' Created on July 25th, 2013

@author: Shveta
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from pages.services_subpages.catalog_subpages.order_service import OrderService


class ServiceCatalogs(Base):
    '''Service -- Service catalog page'''
    _order_button = (By.CSS_SELECTOR, "img[title='Order this Service']")
    _submit_button = (By.CSS_SELECTOR, "img[title='Submit']")
     
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
    
    def select_catalog_item(self, catalog_item_name):
        '''Select catalog Item'''
        number_of_templates = len(OrderService(self).order_catalog_list.items)
        print number_of_templates
        catalog_item = None
        '''First item in list is empty so skipped'''
        for item in OrderService(self).order_catalog_list.items[1:]:
            if item.name == catalog_item_name:
                catalog_item = item
                print "abcd"
                catalog_item.click()
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._order_button).click()
        self._wait_for_results_refresh()
        self.selenium.find_element(*self._submit_button).click()
        self._wait_for_results_refresh()
        print "abcdefhgh"
        from pages.services import Services
        return Services.Requests(self.testsetup)    