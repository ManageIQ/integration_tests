'''
Created on May 6, 2013

@author: bcrochet
'''
from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

class ProvisionCustomize(Base):
    _customize_select_locator = (By.ID, "customize__sysprep_enabled")

    @property
    def customize(self):
        '''Basic Options - Customize
        
        Returns a Select webelement
        '''
        return Select(self.get_element(*self._customize_select_locator))
