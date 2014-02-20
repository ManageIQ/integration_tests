# -*- coding: utf-8 -*-

import operator
from utils.wait import wait_for
from pages.base import Base
from pages.regions.tabbuttonitem import TabButtonItem
from selenium.webdriver.common.by import By
from pages.services import Services
from pages.regions.list import ListItem, ListRegion


class HostProvisionRequests(Services.Requests):
    '''Import of Services.Requests'''

    @property
    def requests_list(self):
        '''Request Item'''
        return ListRegion(
            self.testsetup,
            self.get_element(*self._requests_table),
            self.HostRequestItem)

    def _refresh_and_check_state(self, status):
        self.get_element(*self._reload_button).click()
        self._wait_for_results_refresh()
        latest_item = [item for item in sorted(self.requests_list.items[1:],
            key=operator.attrgetter('request_id'),
            reverse=True)][0]
        if latest_item.approval_state == "Finished":
            if latest_item.status == status:
                return True
            else:
                raise RequestFailedException(latest_item.last_message)
        else:
            return False

    def wait_for_request_status(self, time_period_text, request_status, timeout_in_minutes):
        '''Wait for request status'''
        '''Override'''
        if not self.get_element(*self._check_box_approved).is_selected():
            self.get_element(*self._check_box_approved).click()
        if self.get_element(*self._check_box_denied).is_selected():
            self.get_element(*self._check_box_denied).click()
        if not self.get_element(*self._check_box_pending).is_selected():
            self.get_element(*self._check_box_pending).click()
        self.time_period.select_by_visible_text(time_period_text)

        timeout = 60 * timeout_in_minutes
        wait_for(HostProvisionRequests._refresh_and_check_state, [self, request_status], {},
                 num_sec=timeout, delay=5)
        return self

    class HostRequestItem(ListItem):
        '''Represents a request in the list'''
        _columns = ["view_this_item", "approval_state", "status",
                    "request_id", "requester",
                    "request _type", "completed", "description", "approved_on",
                    "created_on", "last_update", "reason",
                    "last_message", "region"]

        @property
        def view_this_item(self):
            '''View Item'''
            return self._item_data[1].text

        @property
        def status(self):
            '''Status'''
            return self._item_data[2].text

        @property
        def approval_state(self):
            '''Approval State'''
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
            return self._item_data[14].text

        @property
        def region(self):
            '''Region'''
            pass


class HostProvisionFormButtonMixin(object):
    '''Mixin for shared buttons on the Host Provision wizard'''
    _template_submit_button_locator = (
        By.CSS_SELECTOR,
        "li img[alt='Submit this provisioning request']")
    _template_cancel_button_locator = (
        By.CSS_SELECTOR,
        "li img[alt='Cancel this provisioning request']")

    @property
    def submit_button(self):
        '''The continue button. Will select the "visible" one'''
        return self.get_element(*self._template_submit_button_locator)

    @property
    def cancel_button(self):
        '''The cancel button. Will select the "visible" one'''
        return self.get_element(*self._template_cancel_button_locator)

    def click_on_cancel(self):
        ''' Click on cancel button. Go to Hosts page '''
        self.cancel_button.click()
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.hosts import Hosts
        return Hosts(self.testsetup)

    def click_on_submit(self):
        ''' Click on the submit button. Go to Requests page'''
        self.submit_button.click()
        self._wait_for_results_refresh()
        return HostProvisionRequests(self.testsetup)


class HostProvisionTabButtonItem(TabButtonItem):
    '''Specialization of TabButtonItem'''
    from pages.infrastructure_subpages.host_provision_subpages.request \
        import HostProvisionRequest
    from pages.infrastructure_subpages.host_provision_subpages.catalog \
        import HostProvisionCatalog
    from pages.infrastructure_subpages.host_provision_subpages.purpose \
        import HostProvisionPurpose
    from pages.infrastructure_subpages.host_provision_subpages.environment \
        import HostProvisionEnvironment
    from pages.infrastructure_subpages.host_provision_subpages.customize \
        import HostProvisionCustomize
    from pages.infrastructure_subpages.host_provision_subpages.schedule \
        import HostProvisionSchedule

    _item_page = {
        "Request": HostProvisionRequest,
        "Purpose": HostProvisionPurpose,
        "Catalog": HostProvisionCatalog,
        "Environment": HostProvisionEnvironment,
        "Customize": HostProvisionCustomize,
        "Schedule": HostProvisionSchedule
    }


class HostProvision(Base, HostProvisionFormButtonMixin):

    '''Represents the final page in the Provision VM wizard'''
    _page_title = "CloudForms Management Engine: Requests"
    _tab_button_locator = (By.CSS_SELECTOR, "div#prov_tabs > ul > li")

    @property
    def tabbutton_region(self):
        '''Return the tab button region'''
        from pages.regions.tabbuttons import TabButtons
        return TabButtons(self.testsetup,
                locator_override=self._tab_button_locator,
                cls=HostProvisionTabButtonItem)


class RequestFailedException(Exception):
    pass
