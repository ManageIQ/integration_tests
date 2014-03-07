from pages.base import Base
from selenium.webdriver.common.by import By
import re


class RedhatUpdates(Base):
    _page_title = "CloudForms Management Engine: Configuration"
    _edit_registration_button_locator = (By.CSS_SELECTOR, "button#settings_rhn_edit")
    _register_with_locator = (By.CSS_SELECTOR, "select#register_to")
    _address_locator = (By.CSS_SELECTOR, "input#server_url")
    _repo_or_channel_locator = (By.CSS_SELECTOR, "input#repo_name")
    _login_locator = (By.CSS_SELECTOR, "input#customer_userid")
    _password_locator = (By.CSS_SELECTOR, "input#customer_password")
    _organization_locator = (By.CSS_SELECTOR, "input#customer_org")
    _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _url_default_button_locator = (By.CSS_SELECTOR, "button#rhn_default_button")
    _repo_or_channel_default_button_locator = (By.CSS_SELECTOR, "button#repo_default_name")

    _proxy_checkbox_locator = (By.CSS_SELECTOR, "input#use_proxy")
    _proxy_address_locator = (By.CSS_SELECTOR, "input#proxy_address")
    _proxy_username_locator = (By.CSS_SELECTOR, "input#proxy_userid")
    _proxy_password_locator = (By.CSS_SELECTOR, "input#proxy_password")
    _available_version_locator = (By.CSS_SELECTOR, "div#rhn_buttons > table > tbody > tr > td")
    _all_appliances_locator = (By.CSS_SELECTOR, "div#form_div > table > tbody > tr")
    _appliance_checkbox_locator = (By.CSS_SELECTOR, "input#listcheckbox")
    _apply_cfme_updates_button = (By.CSS_SELECTOR, "button#rhn_update_button_on_1")
    _register_button_locator = (By.CSS_SELECTOR, "button#rhn_register_button_on_1")
    _refresh_button_locator = (By.CSS_SELECTOR, "button#rhn_refresh_button")
    _check_for_updates_button_locator = (By.CSS_SELECTOR, "button#rhn_check_updates_button_on_1")

    def select_service(self, service):
        if service == "rhsm":
            self.select_dropdown_by_value("sm_hosted", *self._register_with_locator)
        elif service == "sat5":
            self.select_dropdown_by_value("rhn_satellite", *self._register_with_locator)
        elif service == "sat6":
            self.select_dropdown_by_value("rhn_satellite6", *self._register_with_locator)
        self._wait_for_results_refresh()

    def fill_user_pass_url(self, url, credentials):
        self.fill_field_by_locator(url, *self._address_locator)
        self.fill_field_by_locator(credentials["username"], *self._login_locator)
        self.fill_field_by_locator_with_wait(credentials["password"], *self._password_locator)

    def edit_registration(self,
                          url,
                          credentials,
                          service,
                          organization=None,
                          proxy=None,
                          proxy_creds=None,
                          url_default=False,
                          repo_or_channel=None,
                          repo_or_channel_default=False):
        self.get_element(*self._edit_registration_button_locator).click()
        self._wait_for_results_refresh()
        self.select_service(service)
        self.fill_user_pass_url(url, credentials)
        #Default url available only when registering with rhsm
        if service == 'rhsm' and url_default:
            self.get_element(*self._url_default_button_locator).click()
            self._wait_for_results_refresh()
        elif service == "sat5" and organization:
            self.fill_field_by_locator_with_wait(organization, *self._organization_locator)
        if repo_or_channel:
            self.fill_field_by_locator_with_wait(repo_or_channel, *self._repo_or_channel_locator)
        if repo_or_channel_default:
            self.get_element(*self._repo_or_channel_default_button_locator).click()
            self._wait_for_results_refresh()
        if proxy:
            self.get_element(*self._proxy_checkbox_locator).click()
            self._wait_for_results_refresh()
            self.fill_field_by_locator_with_wait(proxy["url"], *self._proxy_address_locator)
            if proxy_creds:
                self.fill_field_by_locator(proxy_creds["username"],
                                           *self._proxy_username_locator)
                self.fill_field_by_locator_with_wait(proxy_creds["password"],
                                                     *self._proxy_password_locator)

    @property
    def appliances_by_name(self):
        appliances = {}
        for appliance_elem in self.selenium.find_elements(*self._all_appliances_locator):
            appliance = RedhatUpdates.ApplianceItem(self.testsetup, appliance_elem)
            appliances[appliance.name] = appliance
        return appliances

    def select_appliances(self, appliance_names=None):
        """ Marks checkboxes of (all|all given) appliances

        Args:
            appliance_names: List of names of appliances to register
        """
        for appliance_name in appliance_names or self.appliances_by_name.iterkeys():
            self.appliances_by_name[appliance_name].check()

    def appliances_registered(self, appliance_names=None):
        """ Checks if (all|all given) appliances are registered

        Args:
            appliance_names: List of names of appliances to check
        """
        for appliance_name in appliance_names or self.appliances_by_name.iterkeys():
            if not self.appliances_by_name[appliance_name].is_registered:
                return False
        return True

    def appliances_subscribed(self, appliance_names=None):
        """ Checks if (all|all given) appliances are subscribed (or subscribed via proxy)

        Args:
            appliance_names: List of names of appliances to check
        """
        for appliance_name in appliance_names or self.appliances_by_name.iterkeys():
            if not self.appliances_by_name[appliance_name].is_subscribed:
                return False
        return True

    def check_versions(self, appliance_names, expected_version):
        """ Checks if versions match expected version for all given appliances

        Args:
            appliance_names: List of names of appliances to check
            expected_version: Version to match against
        """
        for appliance_name in appliance_names:
            if self.appliances_by_name[appliance_name].version != expected_version:
                return False
        return True

    def platform_updates_available(self, appliance_names=None):
        """ Checks if there are platform updates available for (any|any given) appliances

        Args:
            appliance_names: List of names of appliances to check
        """
        for appliance_name in appliance_names or self.appliances_by_name.iterkeys():
            if self.appliances_by_name[appliance_name].updates_available:
                return True
        return False

    def platform_updates_checked(self, appliance_names=None):
        """ Checks if there is a date in the 'last checked' field for (all|all given) appliances

        Args:
            appliance_names: List of names of appliances to check
        """
        for appliance_name in appliance_names or self.appliances_by_name.iterkeys():
            if not self.appliances_by_name[appliance_name].last_checked:
                return False
        return True

    def save(self):
        self.get_element(*self._save_button_locator).click()
        self._wait_for_results_refresh()
        return RedhatUpdates.Registered(self.testsetup)

    @property
    def available_version(self):
        available_version_raw = self.get_element(*self._available_version_locator).text
        available_version_search_res = re.search(r"([0-9]+\.)*[0-9]+", available_version_raw)
        if available_version_search_res:
            return available_version_search_res.group(0)
        return ""

    def refresh_list(self):
        self.get_element(*self._refresh_button_locator).click()
        self._wait_for_results_refresh()

    def register(self):
        self.get_element(*self._register_button_locator).click()
        self._wait_for_results_refresh()

    def check_updates(self):
        self.get_element(*self._check_for_updates_button_locator).click()
        self._wait_for_results_refresh()

    def apply_cfme_updates(self):
        self.get_element(*self._apply_cfme_updates_button).click()
        self._wait_for_results_refresh()

    class ApplianceItem(Base):
        _checkbox_locator = (By.CSS_SELECTOR, "td:nth-of-type(1) > input")
        _name_locator = (By.CSS_SELECTOR, "td:nth-of-type(2)")
        _zone_locator = (By.CSS_SELECTOR, "td:nth-of-type(3)")
        _status_locator = (By.CSS_SELECTOR, "td:nth-of-type(4)")
        _last_checked_locator = (By.CSS_SELECTOR, "td:nth-of-type(5)")
        _version_locator = (By.CSS_SELECTOR, "td:nth-of-type(6)")
        _updates_available_locator = (By.CSS_SELECTOR, "td:nth-of-type(7)")

        @property
        def checkbox(self):
            return self._root_element.find_element(*self._checkbox_locator)

        @property
        def name(self):
            return self._root_element.find_element(*self._name_locator).text

        @property
        def zone(self):
            return self._root_element.find_element(*self._zone_locator).text

        @property
        def status(self):
            """
            Possible statuses:
              Not registered > Unsubscribed > Subscribed / Subscribed via Proxy
            """
            return self._root_element.find_element(*self._status_locator).text

        @property
        def last_checked(self):
            return self._root_element.find_element(*self._last_checked_locator).text

        @property
        def version(self):
            return self._root_element.find_element(*self._version_locator).text

        @property
        def updates_available(self):
            return self._root_element.find_element(*self._updates_available_locator).text \
                == "Yes"

        @property
        def is_registered(self):
            return self.status != 'Not registered'

        @property
        def is_subscribed(self):
            return self.is_registered and self.status != 'Unsubscribed'

        @property
        def is_checked(self):
            return self.checkbox.is_selected()

        def check(self):
            if not self.is_checked:
                self.checkbox.click()

        def uncheck(self):
            if self.is_checked:
                self.checkbox.click()

    class Registered(Base):
        pass

    class Cancelled(Base):
        pass
