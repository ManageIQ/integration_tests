# -*- coding: utf-8 -*-

from pages.base import Base
from selenium.webdriver.common.by import By


class Edit(Base):
    '''Edit Infrastructure Host page'''
    _page_title = 'CloudForms Management Engine: Hosts'
    _save_button_locator = (By.CSS_SELECTOR,
        "div#buttons_on > ul#form_buttons > li > img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR,
        "ul#form_buttons > li > img[title='Cancel']")
    _name_edit_field_locator = (By.ID, "name")
    _hostname_edit_field_locator = (By.ID, "hostname")
    _ipaddress_edit_field_locator = (By.ID, "ipaddress")
    _default_userid_edit_field_locator = (By.ID, "default_userid")
    _default_password_edit_field_locator = (By.ID, "default_password")
    _default_verify_edit_field_locator = (By.ID, "default_verify")

    @property
    def name(self):
        '''Host name'''
        return self.get_element(*self._name_edit_field_locator)

    @property
    def hostname(self):
        '''Host hostname'''
        return self.get_element(*self._hostname_edit_field_locator)

    @property
    def ipaddress(self):
        '''Host ip address'''
        return self.get_element(*self._ipaddress_edit_field_locator)

    @property
    def default_userid(self):
        '''Host user id'''
        return self.get_element(*self._default_userid_edit_field_locator)

    @property
    def default_password(self):
        '''Host password'''
        return self.get_element(*self._default_password_edit_field_locator)

    @property
    def default_verify(self):
        '''Host password verify'''
        return self.get_element(*self._default_verify_edit_field_locator)

    def edit_host(self, host):
        '''Edit a host given a host dict'''
        for key, value in host.iteritems():
            # Special cases
            if "credentials" in key:
                # use credentials
                credentials = self.testsetup.credentials[value]
                self.default_userid.clear()
                self.default_userid.send_keys(credentials['username'])
                self.default_password.clear()
                self.default_password.send_keys(credentials['password'])
                self.default_verify.clear()
                self.default_verify.send_keys(credentials['password'])
            else:
                # Skip name
                if "name" in key:
                    continue
                # Only try to send keys if there is actually a property
                if hasattr(self, key):
                    attr = getattr(self, key)
                    attr.clear()
                    attr.send_keys(value)

    @property
    def save_button(self):
        '''Save button'''
        return self.get_element(*self._save_button_locator)

    @property
    def cancel_button(self):
        '''Cancel button'''
        return self.get_element(*self._cancel_button_locator)

    def click_on_save(self):
        '''Click on save button'''
        from pages.infrastructure_subpages.hosts_subpages.detail import Detail
        self._wait_for_visible_element(*self._save_button_locator)
        self.save_button.click()
        self._wait_for_results_refresh()
        return Detail(self.testsetup)

    def click_on_cancel(self):
        '''Click on cancel button'''
        from pages.infrastructure_subpages.hosts_subpages.detail import Detail
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return Detail(self.testsetup)
