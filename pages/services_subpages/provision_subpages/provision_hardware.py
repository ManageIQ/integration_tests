'''
Created on May 6, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ProvisionHardware(Base, ProvisionFormButtonMixin):
    '''Provision Wizard - Hardware tab'''
    _number_of_sockets_select_locator = (By.ID, "hardware__number_of_sockets")
    _cores_per_socket_select_locator = (By.ID, "hardware__cores_per_socket")
    _memory_select_locator = (By.ID, "hardware__vm_memory")
    _disk_format_radio_locator = (
            By.CSS_SELECTOR, "input[name='hardware__disk_format']")
    _cpu_limit_input_locator = (By.ID, "hardware__cpu_limit")
    _memory_limit_input_locator = (By.ID, "hardware__memory_limit")
    _cpu_reserve_input_locator = (By.ID, "hardware__cpu_reserve")
    _memory_reserve_input_locator = (By.ID, "hardware__memory_reserve")

    @property
    def number_of_sockets(self):
        '''VM Hardware - Number of sockets'''
        return Select(
                self.get_element(*self._number_of_sockets_select_locator))

    @property
    def cores_per_socket(self):
        '''VM Hardware - Cores per socket'''
        return Select(
                self.get_element(*self._cores_per_socket_select_locator))

    @property
    def memory(self):
        '''VM Hardware - Memory'''
        return Select(self.get_element(*self._memory_select_locator))

    @property
    def disk_format(self):
        '''VM Hardware - Disk Format
        
        Returns a list of elements for the radio buttons
        '''
        return self.selenium.find_elements(*self._disk_format_radio_locator)

    @property
    def cpu_limit(self):
        '''VM Limits - CPU Limit'''
        return self.get_element(*self._cpu_limit_input_locator)

    @property
    def memory_limit(self):
        '''VM Limits - Memory Limit'''
        return self.get_element(*self._memory_limit_input_locator)

    @property
    def cpu_reserve(self):
        '''VM Reservations - CPU'''
        return self.get_element(*self._cpu_reserve_input_locator)

    @property
    def memory_reserve(self):
        '''VM Reservations - Memory'''
        return self.get_element(*self._memory_reserve_input_locator)
