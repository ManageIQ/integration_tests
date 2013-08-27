from pages.base import Base
from selenium.webdriver.common.by import By

class RedhatUpdates(Base):
    _edit_registration_button_locator = (By.CSS_SELECTOR,
            "button#settings_rhn_edit")
    _register_with_locator = (By.CSS_SELECTOR, "select#register_to")
    _address_locator = (By.CSS_SELECTOR, "input#server_url")
    _login_locator = (By.CSS_SELECTOR, "input#customer_userid")
    _password_locator = (By.CSS_SELECTOR, "input#customer_password")
    _save_button_locator = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _cancel_button_locator = (By.CSS_SELECTOR, "img[title='Cancel']")

    _cfme_version_locator = (By.CSS_SELECTOR, "div#form_div > table > tbody \
            > tr:nth-of-type(2) > td:nth-of-type(6)")
    _appliance_checkbox_locator = (By.CSS_SELECTOR, "input#listcheckbox")
    _apply_cfme_updates_button = (By.CSS_SELECTOR, "button#rhn_update_button_on_1")

    def select_service(self, service):
        if service == "rhsm":
            self.select_dropdown("Red Hat Subscription Management",
                    *self._register_with_locator)
        elif service == "sat5":
            self.select_dropdown("RHN Satellite v5",
                    *self._register_with_locator)
        elif service == "sat6":
            self.select_dropdown("RHN Satellite v6",
                    *self._register_with_locator)
        self._wait_for_results_refresh()

    def edit_registration(self, url, credentials, service):
        #click on edit registration
        self.selenium.find_element(*self._edit_registration_button_locator).click()
        self._wait_for_results_refresh()
        #register with provider
        self.select_service(service)
        #fill data
        self.fill_field_by_locator(url, *self._address_locator)
        self.fill_field_by_locator(credentials["username"],
                *self._login_locator)
        self.fill_field_by_locator(credentials["password"],
                *self._password_locator)

    def edit_registration_and_save(self, url, credentials, service):
        self.edit_registration(url, credentials, service)
        self._wait_for_visible_element(*self._save_button_locator)
        #click on save
        self.selenium.find_element(*self._save_button_locator).click()
        self._wait_for_results_refresh()
        return RedhatUpdates.Registered(self.testsetup)

    def edit_registration_and_cancel(self, url, credentials, service):
        self.edit_registration(url, credentials, service)
        self._wait_for_visible_element(*self._cancel_button_locator)
        #click on cancel
        self.selenium.find_element(*self._cancel_button_locator).click()
        self._wait_for_results_refresh()
        return RedhatUpdates.Cancelled(self.testsetup)

    def compare_versions(self, version_from_cfme_data):
        version_from_page = self.selenium.find_element(*self._cfme_version_locator).text
        #here we can use compare version function from rpm package
        return version_from_page == version_from_cfme_data

    def apply_updates(self):
        self.selenium.find_element(*self._appliance_checkbox_locator).click()
        self._wait_for_visible_element(*self._apply_cfme_updates_button)
        self.selenium.find_element(*self._apply_cfme_updates_button).click()
        self._wait_for_results_refresh()

    class Registered(Base):
        pass

    class Cancelled(Base):
        pass

