'''
Created on May 2, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By

class ProvisionRequest(Base):
    '''Provision request tab'''
    _email_input_locator = (By.ID, "requester__owner_email")
    _first_name_input_locator = (By.ID, "requester__owner_first_name")
    _last_name_input_locator = (By.ID, "requester__owner_last_name")
    _notes_input_locator = (By.ID, "requester__request_notes")
    _manager_input_locator = (By.ID, "requester__owner_manager")

    @property
    def email(self):
        '''Email input field'''
        return self.get_element(*self._email_input_locator)

    @property
    def first_name(self):
        '''First name input field'''
        return self.get_element(*self._first_name_input_locator)

    @property
    def last_name(self):
        '''Last name input field'''
        return self.get_element(*self._last_name_input_locator)

    @property
    def manager(self):
        '''Manager input field'''
        return self.get_element(*self._manager_input_locator)
