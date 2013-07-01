'''
Created on May 31, 2013

@author: bcrochet
'''
# -*- coding: utf8 -*-
from pages.base import Base
from pages.infrastructure_subpages.provider_subpages.detail\
    import ProvidersDetail
from selenium.webdriver.common.by import By

class ProvidersEdit(Base):
    '''Edit Infrastructure Provider page'''
    _page_title = 'CloudForms Management Engine: Infrastructure Providers'
    _save_button_locator = (
            By.CSS_SELECTOR,
            "div#buttons_on > ul#form_buttons > li > img[title='Save Changes']")
    _cancel_button_locator = (
            By.CSS_SELECTOR, "ul#form_buttons > li > img[title='Cancel']")
    _name_edit_field_locator = (By.ID, "name")
    _hostname_edit_field_locator = (By.ID, "hostname")
    _ipaddress_edit_field_locator = (By.ID, "ipaddress")
    _server_zone_edit_field_locator = (By.ID, "server_zone")
    _host_default_vnc_port_start_edit_field_locator = (
            By.ID, "host_default_vnc_port_start")
    _host_default_vnc_port_end_edit_field_locator = (
            By.ID, "host_default_vnc_port_end")
    _default_userid_edit_field_locator = (By.ID, "default_userid")
    _default_password_edit_field_locator = (By.ID, "default_password")
    _default_verify_edit_field_locator = (By.ID, "default_verify")

    @property
    def name(self):
        '''Infrastructure Provider name'''
        return self.get_element(*self._name_edit_field_locator)

    @property
    def hostname(self):
        '''Infrastructure Provider hostname'''
        return self.get_element(*self._hostname_edit_field_locator)

    @property
    def ipaddress(self):
        '''Infrastructure Provider ip address'''
        return self.get_element(*self._ipaddress_edit_field_locator)

    @property
    def server_zone(self):
        '''Infrastructure Provider zone'''
        return self.get_element(*self._server_zone_edit_field_locator)

    @property
    def host_default_vnc_port_start(self):
        '''Infrastructure Provider VNC port start'''
        return self.get_element(
                *self._host_default_vnc_port_start_edit_field_locator)

    @property
    def host_default_vnc_port_end(self):
        '''Infrastructure Provider VNC port end'''
        return self.get_element(
                *self._host_default_vnc_port_end_edit_field_locator)

    @property
    def default_userid(self):
        '''Infrastructure Provider user id'''
        return self.get_element(*self._default_userid_edit_field_locator)

    @property
    def default_password(self):
        '''Infrastructure Provider password'''
        return self.get_element(*self._default_password_edit_field_locator)

    @property
    def default_verify(self):
        '''Infrastructure Provider password verify'''
        return self.get_element(*self._default_verify_edit_field_locator)

    def edit_provider(self, provider):
        '''Edit a provider given a provider dict'''
        for key, value in provider.iteritems():
            # Special cases
            if "host_vnc_port" in key:
                self.host_default_vnc_port_start.clear()
                self.host_default_vnc_port_start.send_keys(value["start"])
                self.host_default_vnc_port_end.clear()
                self.host_default_vnc_port_end.send_keys(value["end"])
            elif "server_zone" in key:
                if self.server_zone.tag_name == "select":
                    self.select_dropdown(value)
            elif "edit_name" in key:
                self.name.clear()
                self.name.send_keys(value)
            elif "credentials" in key:
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
        self._wait_for_visible_element(*self._save_button_locator)
        return self.click_on_save()

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
        self.save_button.click()
        self._wait_for_results_refresh()
        return ProvidersDetail(self.testsetup)

    def click_on_cancel(self):
        '''Click on cancel button'''
        self.cancel_button.click()
        self._wait_for_results_refresh()
        from pages.infrastructure_subpages.providers import Providers
        return Providers(self.testsetup)

