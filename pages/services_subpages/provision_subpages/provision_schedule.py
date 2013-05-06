'''
Created on May 6, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ProvisionSchedule(Base):
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

    @property
    def power_on_after_creation(self):
        '''Lifespan - Power on virtual machine after creation'''
        return self.get_element(*self._power_on_checkbox_locator)

    @property
    def retirement(self):
        '''Lifespan - Time until Retirement
        
        Returns a Select webelement
        '''
        return Select(self.get_element(*self._retirement_select_locator))
