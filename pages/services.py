# -*- coding: utf-8 -*-

import re
import time
import operator
from time import sleep
from pages.base import Base
from pages.regions.quadicons import Quadicons
from pages.regions.quadiconitem import QuadiconItem
from pages.regions.paginator import PaginatorMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from pages.regions.list import ListRegion, ListItem
from selenium.webdriver.support.select import Select
from pages.services_subpages.catalog_subpages.catalogs import Catalogs
from pages.services_subpages.catalog_subpages.catalog_items import CatalogItems
from pages.services_subpages.catalog_subpages.service_catalogs \
    import ServiceCatalogs

class Services(Base):
    '''Services page'''
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

        _page_title = 'CloudForms Management Engine: Services'

    class Requests(Base, PaginatorMixin):
        '''Requests page'''
        _page_title = 'CloudForms Management Engine: Requests'
        _requests_table = (
            By.CSS_SELECTOR,
            "div#list_grid > div.objbox > table > tbody")
        _check_box_approved = (By.ID, "state_choice__approved")
        _check_box_denied = (By.ID, "state_choice__denied")
        _check_box_pending = (By.ID, "state_choice__pending_approval")
        _reload_button = (
            By.CSS_SELECTOR,
            "div#center_tb > div.float_left \
            > div[title='Reload the current display']")
        _request_id_heading = (
            By.CSS_SELECTOR,
            "div#list_grid > div.xhdr > table.hdr \
            > tbody > tr > td> div[innertext='Request ID']")
        _approve_this_request_button = (
            By.CSS_SELECTOR,
            "div#center_tb > div.float_left \
            > div[title='Approve this Request']")
        _reason_text_field = (By.ID, "reason")
        _submit_button = (By.CSS_SELECTOR,
            "span#buttons_on > a > img[alt='Submit']")
        _time_period_select_locator = (By.ID, "time_period")

        @property
        def requests_list(self):
            '''Request Item'''
            return ListRegion(
                self.testsetup,
                self.get_element(*self._requests_table),
                Services.RequestItem)

        @property
        def flash(self):
            '''Flash Message Region'''
            return Base.FlashRegion(self.testsetup)

        @property
        def flash_message(self):
            '''Flash Message'''
            return self.flash.message

        @property
        def time_period(self):
            '''Select - Time Period for Requests
            Returns a Select webelement
            '''
            return Select(self.get_element(*self._time_period_select_locator))

        def approve_request(self, item_number):
            '''Approve request'''
            self.get_element(*self._check_box_approved).click()
            self.get_element(*self._check_box_denied).click()
            self.get_element(*self._reload_button).click()
            self._wait_for_results_refresh()

            if self.requests_list.items[item_number].approval_state is not None:
                self.requests_list.items[
                    item_number].approval_state\
                    .find_element_by_tag_name('img').click()
                self.selenium.find_element(
                    *self._approve_this_request_button).click()
                self._wait_for_results_refresh()
                self.selenium.find_element(
                    *self._reason_text_field).send_keys("Test provisioning")
                self._wait_for_results_refresh()
                self._wait_for_visible_element(*self._submit_button)
                self.selenium.find_element(*self._submit_button).click()
                self._wait_for_results_refresh()
            return Services.Requests(self.testsetup)

        def wait_for_request_status(self, time_period_text,
            request_status, timeout_in_minutes):
            '''Wait for request status'''
            if not self.get_element(*self._check_box_approved).is_selected():
                self.get_element(*self._check_box_approved).click()
            if self.get_element(*self._check_box_denied).is_selected():
                self.get_element(*self._check_box_denied).click()
            if not self.get_element(*self._check_box_pending).is_selected():
                self.get_element(*self._check_box_pending).click()
            self.time_period.select_by_visible_text(time_period_text)
            self.get_element(*self._reload_button).click()
            self._wait_for_results_refresh()

            data = {}
            requests_items = self.requests_list.items
            for i in range(1, len(requests_items)):
                data.update({i:requests_items[i].request_id})
            sorted_data = sorted(data.iteritems(), \
                key=operator.itemgetter(1), reverse=True)
            requests_index = sorted_data[0][0]
            minute_count = 0
            while (minute_count < timeout_in_minutes):
                if self.requests_list.items[requests_index]\
                    .status == request_status:
                    break
                print "Waiting for provisioning status: " + request_status
                sleep(60)
                self.time_period.select_by_visible_text(time_period_text)
                self.get_element(*self._reload_button).click()
                self._wait_for_results_refresh()
                if (minute_count==timeout_in_minutes) and \
                   (self.requests_list.items[requests_index]\
                    .status != request_status):
                    raise Exception("timeout reached("+str(timeout_in_minutes)+
                       " minutes) before desired state (" +
                       request_status +") reached... current state("+
                       self.requests_list.items[requests_index].status +")")
            return Services.Requests(self.testsetup)

    class RequestItem(ListItem):
        '''Represents a request in the list'''
        _columns = ["view_this_item", "approval_state", "status",
                    "request_id", "requester",
                    "request _type", "completed", "description", "approved_on",
                    "created_on", "last_update", "reason",
                    "last_message", "region"]

        @property
        def view_this_item(self):
            '''View Item'''
            return self._item_data[0].text

        @property
        def approval_state(self):
            '''Approval State'''
            return self._item_data[1]

        @property
        def status(self):
            '''Status'''
            return self._item_data[2].text

        @property
        def request_id(self):
            '''request Id'''
            return self._item_data[3].text

        @property
        def requester(self):
            '''Requester'''
            pass

        @property
        def request_type(self):
            '''Request Type'''
            pass

        @property
        def completed(self):
            '''Completed'''
            pass

        @property
        def description(self):
            '''Desc'''
            pass

        @property
        def approved_on(self):
            '''Aproved On'''
            pass

        @property
        def created_on(self):
            '''Created On'''
            pass

        @property
        def last_update(self):
            '''Last Updated'''
            pass

        @property
        def reason(self):
            '''Reason'''
            pass

        @property
        def last_message(self):
            '''Last_message'''
            pass

        @property
        def region(self):
            '''Region'''
            pass


    class Catalogs(Base):
        '''Service -- Catalogs'''
        _page_title = 'CloudForms Management Engine: Catalogs'
           
        @property
        def accordion(self):
            '''accordion'''
            from pages.regions.accordion import Accordion
            return Accordion(self.testsetup)

        def click_on_catalogs_accordion(self):
            '''Catalogs accordion'''
            self.accordion.accordion_by_name('Catalogs').click()
            self._wait_for_results_refresh()
            return Catalogs(self.testsetup)

        def click_on_catalog_item_accordion(self):
            '''Ctalog Item accordion'''
            self.accordion.accordion_by_name('Catalog Items').click()
            self._wait_for_results_refresh()
            return CatalogItems(self.testsetup)

        def click_on_service_catalogs_accordion(self):
            '''Service Catalog accordion'''
            self.accordion.accordion_by_name('Service Catalogs').click()
            self._wait_for_results_refresh()
            return ServiceCatalogs(self.testsetup)

