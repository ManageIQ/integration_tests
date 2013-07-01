'''
Created on May 6, 2013

@author: bcrochet
'''
from pages.base import Base
from pages.services_subpages.provision import ProvisionFormButtonMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ProvisionCustomize(Base, ProvisionFormButtonMixin):
    _customize_select_locator = (By.ID, "customize__sysprep_enabled")

    @property
    def customize(self):
        '''Basic Options - Customize
        
        Returns a Select webelement
        '''
        return Select(self.get_element(*self._customize_select_locator))
