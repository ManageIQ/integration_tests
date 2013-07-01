'''
Created on May 6, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ProvisionNetwork(Base, ProvisionFormButtonMixin):
    '''Provison wizard - Network tab'''

    _vlan_select_locator = (By.ID, "network__vlan")

    @property
    def vlan(self):
        '''Network Adapter Information - vLan
        
        Returns Select webelement'''
        return Select(self.get_element(*self._vlan_select_locator))
