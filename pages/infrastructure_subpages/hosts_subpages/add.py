from pages.base import Base
from selenium.webdriver.common.by import By
from unittestzero import Assert


class Add(Base):
    '''Add Infrastructure Host page'''
    _page_title = 'CloudForms Management Engine: Hosts'
    _add_button_locator = (By.CSS_SELECTOR,
        "div#buttons_on > ul#form_buttons > li > img[title='Add this Host']")
    _cancel_button_locator = (By.CSS_SELECTOR,
        "ul#form_buttons > li > img[title='Cancel']")
    _name_add_field_locator = (By.ID, "name")
    _hostname_add_field_locator = (By.ID, "hostname")
    _ipaddress_add_field_locator = (By.ID, "ipaddress")
    _user_assigned_os_add_field_locator = (By.ID, "user_assigned_os")
    _ipmi_address_add_field_locator = (By.ID, "ipmi_address")
    _mac_address_add_field_locator = (By.ID, "mac_address")
    _default_button_locator = (By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#default']")
    _default_userid_add_field_locator = (By.ID, "default_userid")
    _default_password_add_field_locator = (By.ID, "default_password")
    _default_verify_add_field_locator = (By.ID, "default_verify")
    _ipmi_button_locator = (By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#ipmi']")
    _ipmi_userid_add_field_locator = (By.ID, "ipmi_userid")
    _ipmi_password_add_field_locator = (By.ID, "ipmi_password")
    _ipmi_verify_add_field_locator = (By.ID, "ipmi_verify")
    _default_validate_button_locator = (By.CSS_SELECTOR,
                                        "div#default_validate_buttons_on > ul > li > a#val")
    _ipmi_validate_button_locator = (By.CSS_SELECTOR,
                                     "div#ipmi_validate_buttons_on > ul > li > a#val")

    @property
    def name(self):
        '''Host name'''
        return self.get_element(*self._name_add_field_locator)

    @property
    def hostname(self):
        '''Host hostname'''
        return self.get_element(*self._hostname_add_field_locator)

    @property
    def ipaddress(self):
        '''Host ip address'''
        return self.get_element(*self._ipaddress_add_field_locator)

    @property
    def user_assigned_os(self):
        '''Host type'''
        return self.get_element(*self._user_assigned_os_add_field_locator)

    @property
    def ipmi_address(self):
        '''Host ipmi ip address'''
        return self.get_element(*self._ipmi_address_add_field_locator)

    @property
    def mac_address(self):
        '''Host mac address'''
        return self.get_element(*self._mac_address_add_field_locator)

    @property
    def default_button(self):
        '''Default button'''
        return self.get_element(*self._default_button_locator)

    @property
    def default_userid(self):
        '''Host user id'''
        return self.get_element(*self._default_userid_add_field_locator)

    @property
    def default_password(self):
        '''Host password'''
        return self.get_element(*self._default_password_add_field_locator)

    @property
    def default_verify(self):
        '''Host password verify'''
        return self.get_element(*self._default_verify_add_field_locator)

    @property
    def default_validate(self):
        '''Default validate button'''
        return self.get_element(*self._default_validate_button_locator)

    @property
    def ipmi_userid(self):
        '''Host user id'''
        return self.get_element(*self._ipmi_userid_add_field_locator)

    @property
    def ipmi_password(self):
        '''Host password'''
        return self.get_element(*self._ipmi_password_add_field_locator)

    @property
    def ipmi_verify(self):
        '''Host password verify'''
        return self.get_element(*self._ipmi_verify_add_field_locator)

    @property
    def ipmi_button(self):
        '''IPMI button'''
        return self.get_element(*self._ipmi_button_locator)

    @property
    def ipmi_validate(self):
        '''IPMI validate button'''
        return self.get_element(*self._ipmi_validate_button_locator)

    def clear_and_add(self, key, value):
        if hasattr(self, key):
            attr = getattr(self, key)
            attr.clear()
            attr.send_keys(value)

    def add_host(self, host):
        '''Add a host given a host dict'''
        [self.clear_and_add(key, value)
         for key, value in host.iteritems()
         if "credentials" not in key
         and "assigned" not in key]

        for key, value in host.iteritems():
            # Special cases
            if key == "credentials":
                # use credentials
                self.default_button.click()
                self._wait_for_visible_element(*self._default_verify_add_field_locator)
                credentials = self.testsetup.credentials[value]
                self.default_userid.clear()
                self.default_userid.send_keys(credentials['username'])
                self.default_password.clear()
                self.default_password.send_keys(credentials['password'])
                self.default_verify.clear()
                self.default_verify.send_keys(credentials['password'])

                # Because of the way that the data is entered, the button flicks off
                # before flicking on again, this captures that behavior
                self._wait_for_invisible_element(*self._default_validate_button_locator)
                self._wait_for_visible_element(*self._default_validate_button_locator)
                self.default_validate.click()
                self._wait_for_results_refresh()
                Assert.equal('Credential validation was successful', self.flash.message,
                             'Credential validation message should appear')
            elif key == "ipmi_credentials":
                self.ipmi_button.click()
                self._wait_for_visible_element(*self._ipmi_verify_add_field_locator)
                credentials = self.testsetup.credentials[value]
                self.ipmi_userid.clear()
                self.ipmi_userid.send_keys(credentials['username'])
                self.ipmi_password.clear()
                self.ipmi_password.send_keys(credentials['password'])
                self.ipmi_verify.clear()
                self.ipmi_verify.send_keys(credentials['password'])

                # Because of the way that the data is entered, the button flicks off
                # before flicking on again, this captures that behavior
                self._wait_for_invisible_element(*self._ipmi_validate_button_locator)
                self._wait_for_visible_element(*self._ipmi_validate_button_locator)
                self.ipmi_validate.click()
                self._wait_for_results_refresh()
                Assert.equal('Credential validation was successful', self.flash.message,
                             'IPMI Credential validation message should appear')
            elif key == "user_assigned_os":
                self.select_host_platform_type(value)

    @property
    def add_button(self):
        '''Save button'''
        return self.get_element(*self._add_button_locator)

    @property
    def cancel_button(self):
        '''Cancel button'''
        return self.get_element(*self._cancel_button_locator)

    def click_on_add(self):
        '''Click on save button'''
        from pages.infrastructure_subpages.hosts import Hosts
        self._wait_for_visible_element(*self._add_button_locator)
        self.add_button.click()
        self._wait_for_results_refresh()
        return Hosts(self.testsetup)

    def click_on_cancel(self):
        '''Click on cancel button'''
        from pages.infrastructure_subpages.hosts import Hosts
        self.cancel_button.click()
        self._wait_for_results_refresh()
        return Hosts(self.testsetup)

    def select_host_platform_type(self, host_type):
        '''Select a host type from the dropdown,
        and wait for the page to refresh'''
        self.select_dropdown(host_type, *self._user_assigned_os_add_field_locator)
        return True
