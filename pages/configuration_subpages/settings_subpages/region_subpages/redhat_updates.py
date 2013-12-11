from pages.base import Base
from selenium.webdriver.common.by import By


class RedhatUpdates(Base):
    _page_title = "CloudForms Management Engine: Configuration"
    _edit_registration_button_locator = (By.CSS_SELECTOR,
                                         "button#settings_rhn_edit")
    _register_with_locator = (By.CSS_SELECTOR, "select#register_to")
    _address_locator = (By.CSS_SELECTOR, "input#server_url")
    _login_locator = (By.CSS_SELECTOR, "input#customer_userid")
    _password_locator = (By.CSS_SELECTOR, "input#customer_password")
    _organization_locator = (By.CSS_SELECTOR, "input#customer_org")
    _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")
    _default_button_locator = (By.CSS_SELECTOR, "button#rhn_default_button")
    _proxy_checkbox_locator = (By.CSS_SELECTOR, "input#use_proxy")
    _proxy_address_locator = (By.CSS_SELECTOR, "input#proxy_address")
    _proxy_username_locator = (By.CSS_SELECTOR, "input#proxy_userid")
    _proxy_password_locator = (By.CSS_SELECTOR, "input#proxy_password")
    _all_appliances_locator = (By.CSS_SELECTOR, "div#form_div > table > tbody > tr")
    _appliance_checkbox_locator = (By.CSS_SELECTOR, "input#listcheckbox")
    _apply_cfme_updates_button = (By.CSS_SELECTOR, "button#rhn_update_button_on_1")
    _register_button_locator = (By.CSS_SELECTOR, "button#rhn_register_button_on_1")
    _refresh_button_locator = (By.CSS_SELECTOR, "button#rhn_refresh_button")
    _check_for_updates_button_locator = (By.CSS_SELECTOR, "button#rhn_check_updates_button_on_1")

    def fill_user_pass_url(self, url, credentials):
        self.fill_field_by_locator(url, *self._address_locator)
        self.fill_field_by_locator(credentials["username"],
                                   *self._login_locator)
        self.fill_field_by_locator(credentials["password"],
                                   *self._password_locator)

    def edit_registration(self, url, credentials, service, organization, proxy, proxy_creds):
        self.selenium.find_element(*self._edit_registration_button_locator).click()
        self._wait_for_results_refresh()
        if proxy:
            self._wait_for_results_refresh()
            self.selenium.find_element(*self._proxy_checkbox_locator).click()
            self._wait_for_results_refresh()
            self.fill_field_by_locator(proxy["url"],
                                       *self._proxy_address_locator)
            if proxy_creds:
                self.fill_field_by_locator(proxy_creds["username"],
                                           *self._proxy_username_locator)
                self.fill_field_by_locator(proxy_creds["password"],
                                           *self._proxy_password_locator)
        if service == "rhsm":
            self.select_dropdown("Red Hat Subscription Management",
                                 *self._register_with_locator)
            self.fill_user_pass_url(url, credentials)
        elif service == "sat5":
            self.select_dropdown("RHN Satellite v5",
                                 *self._register_with_locator)
            self.fill_user_pass_url(url, credentials)
            self.fill_field_by_locator(organization, *self._organization_locator)
        elif service == "sat6":
            self.select_dropdown("RHN Satellite v6",
                                 *self._register_with_locator)
            self.fill_user_pass_url(url, credentials)

    def edit_registration_and_save(self, url, credentials, service, organization=None,
                                   proxy=False, proxy_creds=False, default=False):
        self.edit_registration(url, credentials, service, organization, proxy, proxy_creds)
        #Default available only when registering with rhsm
        if default:
            self.selenium.find_element(*self._default_button_locator).click()
            self._wait_for_results_refresh()
        self._wait_for_visible_element(*self._save_button_locator)
        #click on save
        self.selenium.find_element(*self._save_button_locator).click()
        self._wait_for_results_refresh()
        return RedhatUpdates.Registered(self.testsetup)

    @property
    def appliance_list(self):
        return [RedhatUpdates.ApplianceItem(self.testsetup, appliance)
                for appliance in self.selenium.find_elements(
                    *self._all_appliances_locator)]

    def systems_registered(self, appliances=False):
        if appliances:
            for appliance in appliances:
                for appliance_from_list in self.appliance_list:
                    if appliance == appliance_from_list.name:
                        if appliance_from_list.status in \
                                ('Subscribed', 'Unsubscribed'):
                            pass
                        else:
                            return False
        else:
            for appliance_from_list in self.appliance_list:
                if appliance_from_list.status in \
                        ('Subscribed', 'Unsubscribed'):
                    pass
                else:
                    return False
        return True

    def check_versions(self, appliance_data):
        if type(appliance_data) is list:
            for appliance in self.appliance_list:
                for app_data in appliance_data:
                    if appliance.name == app_data['name']:
                        if appliance.version != app_data['version']:
                            return False
        else:
            for appliance in self.appliance_list:
                if appliance.version != appliance_data:
                    return False
        return True

    def register_appliances(self, appliances_to_register=False):
        if appliances_to_register:
            for appliance in self.appliance_list:
                for appliance_to_register in appliances_to_register:
                    if appliance.name == appliance_to_register:
                        appliance.checkbox.click()
        else:
            for appliance in self.appliance_list:
                appliance.checkbox.click()
        self._wait_for_visible_element(*self._register_button_locator)
        self.selenium.find_element(*self._register_button_locator).click()
        self._wait_for_results_refresh()

    def apply_updates(self, appliances_to_update):
        for appliance in self.appliance_list:
            for appliance_to_update in appliances_to_update:
                if appliance.name == appliance_to_update:
                    appliance.checkbox.click()
        self._wait_for_visible_element(*self._apply_cfme_updates_button)
        self.selenium.find_element(*self._apply_cfme_updates_button).click()
        self._wait_for_results_refresh()

    def refresh_list(self):
        self.selenium.find_element(*self._refresh_button_locator).click()
        self._wait_for_results_refresh()

    def platform_updates_available(self, appliances=False):
        if appliances:
            for app_from_list in appliances:
                for appliance in self.appliance_list:
                    if app_from_list['name'] == appliance.name:
                        if appliance.updates_available:
                            return True
        else:
            for appliance in self.appliance_list:
                if appliance.updates_available:
                    return True
        return False

    def refresh_updates(self, first_run, appliances=False):
        if first_run:
            if appliances:
                for app_from_list in appliances:
                    for appliance in self.appliance_list:
                        if app_from_list['name'] == appliance.name:
                            appliance.checkbox.click()
            else:
                for appliance in self.appliance_list:
                    appliance.checkbox.click()
        self.selenium.find_element(*self._check_for_updates_button_locator).click()
        self._wait_for_results_refresh()

    def platform_updates_checked(self, appliances=False):
        if appliances:
            for app_from_list in appliances:
                for appliance in self.appliance_list:
                    if app_from_list['name'] == appliance.name:
                        if appliance.last_checked == '':
                            return False
        else:
            for appliance in self.appliance_list:
                if appliance.last_checked == '':
                    return False
        return True

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

    class Registered(Base):
        pass
