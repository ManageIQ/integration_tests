'''
Created on May 2, 2013

@author: bcrochet
'''

# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By
from pages.services_subpages.provision import ProvisionFormButtonMixin

class ProvisionRequest(Base, ProvisionFormButtonMixin):
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
    def notes(self):
        '''Notse input field'''
        return self.get_element(*self._notes_input_locator)

    @property
    def manager(self):
        '''Manager input field'''
        return self.get_element(*self._manager_input_locator)

    def fill_fields(
            self,
            email_text,
            first_name_text,
            last_name_text,
            notes_text,
            manager_text):
        self._wait_for_results_refresh()
        self.email.send_keys(email_text)
        self.first_name.send_keys(first_name_text)
        self.last_name.send_keys(last_name_text)
        self.notes.send_keys(notes_text)
        self.manager.send_keys(manager_text)
        return self.testsetup
