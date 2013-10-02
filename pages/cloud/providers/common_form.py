from pages.base import Base
from selenium.webdriver.common.by import By

# pylint: disable=R0904
# pylint: disable=C0103

class AddFormCommon(Base):
    '''Cloud Providers - Add an Cloud Provider page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'

    _provider_credentials_verify_button_locator = (
            By.CSS_SELECTOR,
            "div#default_validate_buttons_on > ul#form_buttons > li > a > img")
    _provider_credentials_verify_disabled_button_locator = (
            By.CSS_SELECTOR,
            "div#default_validate_buttons_off > ul#form_buttons > li > a > img")
    _provider_cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _provider_name_locator = (By.ID, "name")
    _provider_hostname_locator = (By.ID, "hostname")
    _provider_ipaddress_locator = (By.ID, "ipaddress")
    _provider_type_locator = (By.ID, "server_emstype")
    _amazon_region_locator = (By.ID, "hostname")
    _provider_userid_locator = (By.ID, "default_userid")
    _provider_password_locator = (By.ID, "default_password")
    _provider_verify_password_locator = (By.ID, "default_verify")
    _provider_amqp_userid_locator = (By.ID, "amqp_userid")
    _provider_amqp_password_locator = (By.ID, "amqp_password")
    _provider_amqp_verify_locator = (By.ID, "amqp_verify")
    _server_zone_edit_field_locator = (By.ID, "server_zone")
    _default_credentials_button_locator = (
            By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#default']")
    _amqp_credentials_button_locator = (
            By.CSS_SELECTOR, "div#auth_tabs > ul > li > a[href='#amqp']")
    _provider_api_port_locator = (By.ID, "port")

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
        return self.get_element(*self._provider_cancel_button_locator)

    @property
    def name(self):
        '''Name of the cloud provider'''
        return self.get_element(*self._provider_name_locator)

    @property
    def hostname(self):
        '''Hostname of the cloud provider'''
        return self.get_element(*self._provider_hostname_locator)

    @property
    def ipaddress(self):
        '''IP address of the cloud provider'''
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
        return self.get_element(*self._provider_verify_password_locator)

    @property
    def amqp_userid(self):
        '''Userid on amqp credentials tab'''
        return self.get_element(*self._provider_amqp_userid_locator)

    @property
    def amqp_password(self):
        '''Password on amqp credentials tab'''
        return self.get_element(
                *self._provider_amqp_password_locator)

    @property
    def amqp_verify(self):
        '''Verify password on amqp credentials tab'''
        return self.get_element(*self._provider_amqp_verify_locator)

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

    def click_on_amqp_credentials(self):
        '''Click on the Openstack AMQP credentials tab'''
        self.get_element(*self._amqp_credentials_button_locator).click()

    def _fill_provider(self, provider):
        '''Fill a cloud provider given a dictionary'''
        for key, value in provider.iteritems():
            # Special cases
            if "server_zone" in key:
                if self.server_zone.tag_name == "select":
                    self.select_dropdown(value)
            else:
                # Only try to send keys if there is actually a property
                if hasattr(self, key):
                    attr = getattr(self, key)
                    attr.clear()
                    attr.send_keys(value)

            if "amqp_credentials" == key:
                creds = self.testsetup.amqp_credentials[value]
                self.update_amqp_creds(
                    creds['username'], creds['password'], creds['password'])
            elif "credentials" in key:
                creds = self.testsetup.credentials[value]
                self.update_default_creds(
                    creds['username'], creds['password'], creds['password'])
        self._wait_for_results_refresh()

    def update_amqp_creds(self, user, passwd, verify):
        ''' Fill in amqp credentials '''
        self.click_on_amqp_credentials()
        self.fill_field_element(user, self.amqp_userid)
        self.fill_field_element(passwd, self.amqp_password)
        self.fill_field_element(verify, self.amqp_verify)

    def update_default_creds(self, user, passwd, verify):
        ''' Fill in default credentials '''
        self.click_on_default_credentials()
        self.fill_field_element(user, self.default_userid)
        self.fill_field_element(passwd, self.default_password)
        self.fill_field_element(verify, self.default_verify)

    def select_amazon_region(self, region='us-east-1'):
        '''Select a amazon region from the dropdown,
        and wait for the page to refresh'''
        self.select_dropdown_by_value(
                region,
                *self._amazon_region_locator)
        from pages.cloud.providers.add import Add
        return Add(self.testsetup)

    def click_on_credentials_verify(self):
        '''Click on the verify credentials button and wait for page refresh'''
        self.verify_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.providers.add import Add
        return Add(self.testsetup)

    def click_on_cancel(self):
        '''Click on cancel

        Returns Cloud Providers page'''
        self.cancel_button.click()
        from pages.cloud.providers import Providers
        return Providers(self.testsetup)
