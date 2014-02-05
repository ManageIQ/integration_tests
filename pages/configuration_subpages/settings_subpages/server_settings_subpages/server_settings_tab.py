from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from pages.configuration_subpages.settings_subpages.server_settings_subpages.server_roles \
    import ServerRoleList


class ServerSettingsTab(Base, ServerRoleList):
    _page_title = 'CloudForms Management Engine: Configuration'

    _submit_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _reset_button = (By.CSS_SELECTOR, "img[title='Reset Changes']")
    _zone_selector = (By.CSS_SELECTOR, "select[name='server_zone']")

    #Outgoing SMTP E-mail Server
    _host_locator = (By.CSS_SELECTOR, "input#smtp_host")
    _port_locator = (By.CSS_SELECTOR, "input#smtp_port")
    _domain_locator = (By.CSS_SELECTOR, "input#smtp_domain")
    _start_tls_checkbox_locator = (By.CSS_SELECTOR,
            "input#smtp_enable_starttls_auto")
    _ssl_verify_mode_dropdown_locator = (By.CSS_SELECTOR,
            "select#smtp_openssl_verify_mode")
    _authentication_dropdown_locator = (By.CSS_SELECTOR,
            "select#smtp_authentication")
    _user_name_locator = (By.CSS_SELECTOR, "input#smtp_user_name")
    _password_locator = (By.CSS_SELECTOR, "input#smtp_password")
    _from_email_address_locator = (By.CSS_SELECTOR, "input#smtp_from")
    _test_email_address_locator = (By.CSS_SELECTOR, "input#smtp_test_to")
    _server_name_locator = (By.CSS_SELECTOR, "input#server_name")

    def save(self):
        self._wait_for_visible_element(*self._submit_button)
        self.selenium.find_element(*self._submit_button).click()
        self._wait_for_results_refresh()
        return ServerSettingsTab(self.testsetup)

    def click_on_reset(self):
        self._wait_for_visible_element(*self._reset_button)
        self.selenium.find_element(*self._reset_button).click()
        self._wait_for_results_refresh()

    def set_zone(self, zone):
        Select(self.selenium.find_element(*self._zone_selector)).select_by_value(zone)

    def setup_outgoing_smtp_email_server(self, host, port, domain, tls, ssl_mode,
            authentication, user_name, password, from_email, test_email):
        #host
        self.fill_field_by_locator(host, *self._host_locator)
        #port
        self.fill_field_by_locator(port, *self._port_locator)
        #domain
        self.fill_field_by_locator(domain, *self._domain_locator)
        #tls checkbox
        if tls == 'False':
            self.selenium.find_element(*self._start_tls_checkbox_locator).click()
        #ssl verify mode
        self.select_dropdown(ssl_mode, *self._ssl_verify_mode_dropdown_locator)
        #authentication
        self.select_dropdown(authentication, *self._authentication_dropdown_locator)
        #user name
        self.fill_field_by_locator(user_name, *self._user_name_locator)
        #password
        self.fill_field_by_locator(password, *self._password_locator)
        #email - from
        self.fill_field_by_locator(from_email, *self._from_email_address_locator)
        #email - test
        self.fill_field_by_locator(test_email, *self._test_email_address_locator)

    def get_server_name(self):
        server_name_input = self.selenium.find_element(
            *self._server_name_locator)
        return server_name_input.get_attribute('value')

    def set_server_name(self, server_name):
        self.fill_field_by_locator(server_name, *self._server_name_locator)
