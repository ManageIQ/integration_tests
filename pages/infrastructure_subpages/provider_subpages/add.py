'''
Created on May 31, 2013

@author: bcrochet
'''
from pages.base import Base
from selenium.webdriver.common.by import By

class ProvidersAdd(Base):
    '''Infrastructure Providers - Add an Infrastructure Provider page'''
    _page_title = 'CloudForms Management Engine: Infrastructure Providers'

    _provider_add_button_locator = (
            By.CSS_SELECTOR,
            "img[alt='Add this Infrastructure Provider']")
    _provider_credentials_verify_button_locator = (
            By.CSS_SELECTOR,
            "div#default_validate_buttons_on > ul#form_buttons > li > a > img")
    _provider_credentials_verify_disabled_button_locator = (
            By.CSS_SELECTOR,
            "div#default_validate_buttons_off > ul#form_buttons > li > a > img")
    _provider_cancel_button_locator = (
            By.CSS_SELECTOR, "img[title='Cancel']")
    _provider_name_locator = (By.ID, "name")
    _provider_hostname_locator = (By.ID, "hostname")
    _provider_ipaddress_locator = (By.ID, "ipaddress")
    _provider_type_locator = (By.ID, "server_emstype")
    _provider_userid_locator = (By.ID, "default_userid")
    _provider_password_locator = (By.ID, "default_password")
    _provider_verify_password_locator = (By.ID, "default_verify")
    _provider_cu_userid_locator = (By.ID, "metrics_userid")
    _provider_cu_password_locator = (By.ID, "metrics_password")
    _provider_cu_verify_locator = (By.ID, "metrics_verify")
    _server_zone_edit_field_locator = (By.ID, "server_zone")
    _default_credentials_button_locator = (
            By.CSS_SELECTOR, "div#auth_tabs > ul > li > a#ui-id-1")
    _metrics_credentials_button_locator = (
            By.CSS_SELECTOR, "div#auth_tabs > ul > li > a#ui-id-2")
    _provider_api_port_locator = (
            By.ID, "port")

    @property
    def add_button(self):
        '''Add button

        Returns a WebElement'''
        return self.get_element(*self._provider_add_button_locator)

    @property
    def verify_button(self):
        '''Verify button

        Returns a WebElement'''
        return self.get_element(
                *self._provider_credentials_verify_button_locator)

    @property
    def cancel_button(self):
        '''Cancel button

        Returns a WebElement'''
        return self.get_element(
                *self._provider_cancel_button_locator)

    @property
    def name(self):
        '''Name of the infrastructure provider'''
        return self.get_element(*self._provider_name_locator)

    @property
    def hostname(self):
        '''Hostname of the infrastructure provider'''
        return self.get_element(*self._provider_hostname_locator)

    @property
    def ipaddress(self):
        '''IP address of the infrastructure provider'''
        return self.get_element(*self._provider_ipaddress_locator)

    @property
    def default_userid(self):
        '''Userid on default credentials tab'''
        return self.get_element(*self._provider_userid_locator)

    @property
    def default_password(self):
        '''Password on default credentials tab'''
        return self.get_element(*self._provider_password_locator)

    @property
    def default_verify(self):
        '''Verify password on default credentials tab'''
        return self.get_element(
                *self._provider_verify_password_locator)

    @property
    def metrics_userid(self):
        '''Userid on C&U credentials tab'''
        return self.get_element(*self._provider_cu_userid_locator)

    @property
    def metrics_password(self):
        '''Password on C&U credentials tab'''
        return self.get_element(
                *self._provider_cu_password_locator)

    @property
    def metrics_verify(self):
        '''Verify password on C&U credentials tab'''
        return self.get_element(*self._provider_cu_verify_locator)

    @property
    def api_port(self):
        '''API port'''
        return self.get_element(*self._provider_api_port_locator)

    @property
    def server_zone(self):
        '''Zone'''
        return self.get_element(*self._server_zone_edit_field_locator)

    def click_on_default_credentials(self):
        '''Click on the default credentials tab'''
        self.get_element(*self._default_credentials_button_locator).click()

    def click_on_metrics_credentials(self):
        '''Click on the C&U credentials tab'''
        self.get_element(*self._metrics_credentials_button_locator).click()

    def new_provider_fill_data(
            self,
            name="test_name",
            hostname="test_hostname",
            ip_address="127.0.0.1",
            user_id="test_user",
            password="test_password"):
        '''Fill a infrastructure provider with individual args'''
        self.name.send_keys(name)
        self.hostname.send_keys(hostname)
        self.ipaddress.send_keys(ip_address)
        self.default_userid.send_keys(user_id)
        self.default_password.send_keys(password)
        self.default_verify.send_keys(password)

    def _fill_provider(self, provider):
        '''Fill a infrastructure provider given a dictionary'''
        for key, value in provider.iteritems():
            # Special cases
            if "server_zone" in key:
                if self.server_zone.tag_name == "select":
                    self.select_dropdown(value)
            elif "cu_credentials" in key:
                self.click_on_metrics_credentials()
                credentials = self.testsetup.credentials[value]
                self.metrics_userid.clear()
                self.metrics_userid.send_keys(credentials['username'])
                self.metrics_password.clear()
                self.metrics_password.send_keys(credentials['password'])
                self.metrics_verify.clear()
                self.metrics_verify.send_keys(credentials['password'])
                continue
            elif "credentials" in key:
                self.click_on_default_credentials()
                credentials = self.testsetup.credentials[value]
                self.default_userid.clear()
                self.default_userid.send_keys(credentials['username'])
                self.default_password.clear()
                self.default_password.send_keys(credentials['password'])
                self.default_verify.clear()
                self.default_verify.send_keys(credentials['password'])
                continue
            else:
                # Only try to send keys if there is actually a property
                if hasattr(self, key):
                    attr = getattr(self, key)
                    attr.clear()
                    attr.send_keys(value)
        self._wait_for_results_refresh()

    def add_vmware_provider(self, provider):
        '''Fill and click on add for a vmware system'''
        self.select_provider_type("VMware vCenter")
        self._fill_provider(provider)
        return self.click_on_add()

    def add_rhevm_provider(self, provider):
        '''Fill and click on add for a RHEV system'''
        self.select_provider_type(
                "Red Hat Enterprise Virtualization Manager")
        self._fill_provider(provider)
        return self.click_on_add()

    def add_provider(self, provider):
        '''Generic add.

        Will determine the correct infrastructure provider to add'''
        if "virtualcenter" in provider["type"]:
            return self.add_vmware_provider(provider)
        elif "rhevm" in provider["type"]:
            return self.add_rhevm_provider(provider)
        raise Exception("Unknown infrastructure provider type")

    def add_provider_with_bad_credentials(self, provider):
        '''Add a infrastructure provider and click verify,
        expecting bad creds'''
        if "virtualcenter" in provider["type"]:
            self.select_provider_type("VMware vCenter")
        elif "rhevm" in provider["type"]:
            self.select_provider_type(
                    "Red Hat Enterprise Virtualization Manager")
        self._fill_provider(provider)
        self._wait_for_visible_element(
                *self._provider_credentials_verify_button_locator)
        self.click_on_credentials_verify()
        self._wait_for_results_refresh()
        return self

    def select_provider_type(self, provider_type):
        '''Select a infrastructure provider type from the dropdown,
        and wait for the page to refresh'''
        self.select_dropdown(
                provider_type,
                *self._provider_type_locator)
        self._wait_for_results_refresh()
        return ProvidersAdd(self.testsetup)

    def click_on_add(self):
        '''Click on the add button'''
        self.add_button.click()
        from pages.infrastructure_subpages.providers \
                import Providers
        return Providers(self.testsetup)

    def click_on_credentials_verify(self):
        '''Click on the verify credentials button and wait for page refresh'''
        self.verify_button.click()
        self._wait_for_results_refresh()
        return ProvidersAdd(self.testsetup)

    def click_on_cancel(self):
        '''Click on cancel

        Returns Providers page'''
        self.cancel_button.click()
        from pages.infrastructure_subpages.providers \
                import Providers
        return Providers(self.testsetup)

