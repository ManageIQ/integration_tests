# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.infrastructure_subpages.host_provision import HostProvisionFormButtonMixin


class HostProvisionSchedule(Base, HostProvisionFormButtonMixin):
    '''Provision wizard - Schedule tab'''
    _when_to_provision_radio_locator = (
        By.CSS_SELECTOR, "input[name='schedule__schedule_type']")
    _power_on_checkbox_locator = (By.ID, "schedule__vm_auto_start")
    _retirement_select_locator = (By.ID, "schedule__retirement")

    @property
    def when_to_provision(self):
        '''Schedule Info - When to Provision

        Returns a list of elements for the radio buttons
        '''
        return self.selenium.find_elements(
            *self._when_to_provision_radio_locator)

    def select_schedule(self, value):
        for radio in self.when_to_provision:
            if radio.get_attribute('value') == value:
                radio.click()
                return True
        else:
            return False

    def fill_fields(self, when_to_provide):
        self.select_schedule(when_to_provide)
        self._wait_for_results_refresh()
        return HostProvisionSchedule(self.testsetup)
