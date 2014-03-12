# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from cfme.web_ui import paginator
from pages.base import Base
from pages.regions.list import ListRegion, ListItem
from pages.regions.paginator import PaginatorMixin
from pages.services_subpages.catalog_subpages.catalog_items import CatalogItems
from pages.services_subpages.catalog_subpages.catalogs import Catalogs
from pages.services_subpages.catalog_subpages.service_catalogs import ServiceCatalogs
from utils.wait import wait_for


class Services(Base):
    '''Services page'''
    @property
    def submenus(self):
        return {"services": Services.MyServices,
                "catalogs": Services.Catalogs,
                "miq_request_vm": Services.Requests,
                }

    @property
    def is_the_current_page(self):
        '''Override for top-level menu class'''
        return self.current_subpage.is_the_current_page

    class MyServices(Base, PaginatorMixin):

        _page_title = 'CloudForms Management Engine: Services'

        @property
        def accordion(self):
            '''accordion'''
            from pages.regions.accordion import Accordion
            from pages.regions.treeaccordionitem import LegacyTreeAccordionItem
            return Accordion(self.testsetup, LegacyTreeAccordionItem)

        def select_service_in_tree(self, service_name):
            '''Select service'''
            self.accordion.current_content.find_node_by_name(service_name).click()
            self._wait_for_results_refresh()
            return self

        def is_service_present(self, service_name):
            '''Select service'''
            if(self.accordion.current_content.find_node_by_name(service_name)):
                self._wait_for_results_refresh()
                return True
            else:
                return False

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
        _requests_link_locator = (
            By.CSS_SELECTOR,
            "div#breadcrumbs > a")

        @property
        def requests_list(self):
            '''Request Item'''
            return ListRegion(
                self.testsetup,
                self.get_element(*self._requests_table),
                Services.RequestItem)

        @property
        def request_items(self):
            # skip the first item in the list, it's an empty row
            return self.requests_list.items[1:]

        def request_by_id(self, request_id):
            """Loop over request pages and return the request with matching id
            or None if that request isn't found.

            """
            for page in paginator.pages():
                for request_item in self.request_items:
                    if request_item.request_id == request_id:
                        return request_item

        def reload(self):
            self.get_element(*self._reload_button).click()
            self._wait_for_results_refresh()

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
            if not self.get_element(*self._check_box_approved).is_selected():
                self.get_element(*self._check_box_approved).click()
            if self.get_element(*self._check_box_approved).is_selected():
                self.get_element(*self._check_box_denied).click()
            if not self.get_element(*self._check_box_pending).is_selected():
                self.get_element(*self._check_box_pending).click()

            if len(self.requests_list.items) > 0 and \
                    self.requests_list.items[item_number]\
                    .view_this_item is not None:
                request_number = self.requests_list.items[
                    item_number].request_id
                self.requests_list.items[
                    item_number].view_this_item\
                    .find_element_by_tag_name('img').click()

                self._wait_for_visible_element(*self._requests_link_locator)
                if self.is_element_visible(*self._approve_this_request_button):
                    self.selenium.find_element(
                        *self._approve_this_request_button).click()
                    self._wait_for_results_refresh()
                    self.selenium.find_element(
                        *self._reason_text_field).send_keys("Test provisioning")
                    self._wait_for_results_refresh()
                    self._wait_for_visible_element(*self._submit_button)
                    self.selenium.find_element(*self._submit_button).click()
                    self._wait_for_results_refresh()
                else:
                    self.selenium.find_element(
                        *self._requests_link_locator).click()
            return request_number

        def wait_for_request_status(self, time_period_text, request_state, timeout_in_minutes,
                request_number):
            '''Wait for request state to match request_state

            request status must be 'Ok'

            '''
            if not self.get_element(*self._check_box_approved).is_selected():
                self.get_element(*self._check_box_approved).click()
            if self.get_element(*self._check_box_denied).is_selected():
                self.get_element(*self._check_box_denied).click()
            if not self.get_element(*self._check_box_pending).is_selected():
                self.get_element(*self._check_box_pending).click()
            self.time_period.select_by_visible_text(time_period_text)

            def wait_func():
                request = self.request_by_id(request_number)
                if request.status != 'Ok':
                    raise Exception("Status of request is not Ok: %s" %
                        request.request_id)

                if request.request_state != request_state:
                    return False
                else:
                    return request
            wait_for(wait_func, num_sec=timeout_in_minutes * 60, fail_func=self.reload, delay=10)
            return Services.Requests(self.testsetup)

    class RequestItem(ListItem):
        '''Represents a request in the list'''
        _columns = ["view_this_item", "status", "request_state",
                    "request_id", "requester", "request _type",
                    "completed", "description", "approval_state",
                    "approved_on", "created_on", "last_update",
                    "reason", "last_message", "region"]

        @property
        def view_this_item(self):
            '''View Item'''
            return self._item_data[1]

        @property
        def status(self):
            '''Status'''
            return self._item_data[2].text

        @property
        def request_state(self):
            '''Request State'''
            return self._item_data[3].text

        @property
        def request_id(self):
            '''request Id'''
            return self._item_data[4].text

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
        def approval_state(self):
            '''Approval State'''
            return self._item_data[8].text

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
