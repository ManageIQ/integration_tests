from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
import time

class DatabaseSettingsTab(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _dbtype_selector = (By.CSS_SELECTOR, "#production_dbtype")
    _submit_button = (By.CSS_SELECTOR, "img[title='Save changes and restart the Server']")
    _validate_button = (By.CSS_SELECTOR, "img[title='Validate Database Configuration']")


    def set_external_postgres_db(self, hostname, dbname, username, password):
        self._select_dbtype('postgresql')
        self._set_field('production_host', hostname)
        self._set_field('production_database', dbname)
        self._set_field('production_username', username)
        self._set_field('production_password', password)
        self._set_field('production_verify', password)

    def set_external_evm_db(self, hostname):
        self._select_dbtype('external_evm')
        self._set_field('production_host', hostname)

    def set_internal_evm_db(self):
        self._select_dbtype('internal')

    @property
    def dbtype(self):
        return Select(self.selenium.find_element(*self._dbtype_selector)).first_selected_option

    def validate(self):
        self._wait_for_visible_element(*self._validate_button)
        self.selenium.find_element(*self._validate_button).click()
        self._wait_for_results_refresh()
        return DatabaseSettingsTab(self.testsetup)

    def save(self):
        self._wait_for_visible_element(*self._submit_button)
        self.selenium.find_element(*self._submit_button).click()
        self.handle_popup()
        self._wait_for_results_refresh()
        return DatabaseSettingsTab(self.testsetup)

    def _set_field(self, name, val):
        field = self.selenium.find_element_by_name(name)
        field.clear()
        field.send_keys(val)

    def _select_dbtype(self, val):
        Select(self.selenium.find_element(*self._dbtype_selector)).select_by_value(val)
        # TODO: rest of form is loaded on db type change, there is no simple way
        # how to detect that ajax finished
        time.sleep(5)
