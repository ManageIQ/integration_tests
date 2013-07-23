# -*- coding: utf-8 -*-

import re
import time
from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.paginator import PaginatorMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from pages.regions.list import ListRegion, ListItem
from pages.services_subpages.catalog_subpages.catalogs import Catalogs
from pages.services_subpages.catalog_subpages.catalog_items import CatalogItems
from pages.services_subpages.catalog_subpages.service_catalogs import ServiceCatalogs

class Services(Base):
    @property
    def submenus(self):
        return {"services"       : Services.MyServices,
                "catalogs"       : Services.Catalogs,
                "miq_request_vm" : Service.Requests,
                }

    @property
    def is_the_current_page(self):
        '''Override for top-level menu class'''
        return self.current_subpage.is_the_current_page

    class MyServices(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: My Services'

    class Requests(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: Requests'
        _requests_table = (By.CSS_SELECTOR, "div#list_grid > div.objbox > table > tbody")
        _check_box_approved = (By.ID, "state_choice__approved")
        _check_box_denied = (By.ID, "state_choice__denied")
        _reload_button = (By.CSS_SELECTOR, "div#center_tb > div.float_left > div[title='Reload the current display']")
        _approve_this_request_button = (By.CSS_SELECTOR, "div#center_tb > div.float_left > div[title='Approve this Request']")
        _reason_text_field = (By.ID, "reason")
        _submit_button = (By.CSS_SELECTOR, "span#buttons_on > a > img[alt='Submit']")

        @property
        def requests_list(self):
            return ListRegion(
                self.testsetup,
                self.get_element(*self._requests_table),
                Services.RequestItem)

        def approve_request(self, item_number):

            self.get_element(*self._check_box_approved).click()
            self.get_element(*self._check_box_denied).click()
            self.get_element(*self._reload_button).click()
            self._wait_for_results_refresh()

            self.requests_list.items[item_number]._item_data[1].find_element_by_tag_name('img').click()
            self.selenium.find_element(*self._approve_this_request_button).click()
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._reason_text_field).send_keys("Test provisioning")
            self._wait_for_results_refresh()
            self._wait_for_visible_element(*self._submit_button)
            self.selenium.find_element(*self._submit_button).click()
            self._wait_for_results_refresh()
            return Services.Requests(self.testsetup)

    class RequestItem(ListItem):
        '''Represents a request in the list'''
        _columns = ["view_this_item", "status", "request_id", "requester", "request _type", "completed", "description", "approved_on", "created_on", "last_update", "reason", "last_message", "region"]

        @property
        def view_this_item(self):
            return self._item_data[0].text

        @property
        def status(self):
            return self._item_data[1].text

        @property
        def request_id(self):
            pass

        @property
        def requester(self):
            pass

        @property
        def request_type(self):
            pass

        @property
        def completed(self):
            pass

        @property
        def description(self):
            pass

        @property
        def approved_on(self):
            pass

        @property
        def created_on(self):
            pass

        @property
        def last_update(self):
            pass

        @property
        def reason(self):
            pass

        @property
        def last_message(self):
            pass

        @property
        def region(self):
            pass
        
        
    class Catalogs(Base):
        _page_title = 'CloudForms Management Engine: Catalogs'
           
        @property
        def accordion(self):
            from pages.regions.accordion import Accordion
            return Accordion(self.testsetup)

        def click_on_catalogs_accordion(self):
             self.accordion.accordion_by_name('Catalogs').click()
             self._wait_for_results_refresh()
             return Catalogs(self.testsetup)

        def click_on_catalog_item_accordion(self):
            self.accordion.accordion_by_name('Catalog Items').click()
            self._wait_for_results_refresh()
            return CatalogItems(self.testsetup)

        def click_on_service_catalogs_accordion(self):
            self.accordion.accordion_by_name('Service Catalogs').click()
            self._wait_for_results_refresh()
            return ServiceCatalogs(self.testsetup)


