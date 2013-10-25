from pages.base import Base
from selenium.webdriver.common.by import By


class AuthenticationSettingsTab(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _submit_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _reset_button = (By.CSS_SELECTOR, "img[title='Reset Changes']")

    _session_timeout_hours_selector = (By.CSS_SELECTOR, "select#session_timeout_hours")
    _session_timeout_mins_selector = (By.CSS_SELECTOR, "select#session_timeout_mins")
    _auth_mode_selector = (By.CSS_SELECTOR, "select#authentication_mode")

    _ldap_host1_field = (By.CSS_SELECTOR, "input#authentication_ldaphost_1")
    _ldap_host2_field = (By.CSS_SELECTOR, "input#authentication_ldaphost_2")
    _ldap_host3_field = (By.CSS_SELECTOR, "input#authentication_ldaphost_3")
    _ldap_port_field = (By.CSS_SELECTOR, "input#authentication_ldapport")
    _ldap_usertype_selector = (By.CSS_SELECTOR, "select#authentication_user_type")
    _ldap_usersuffix_field = (By.CSS_SELECTOR, "input#authentication_user_suffix")
    _ldap_get_groups_checkbox = (By.CSS_SELECTOR, "input#ldap_role")
    _ldap_get_roles_forest_checkbox = (By.CSS_SELECTOR, "input#get_direct_groups")
    _ldap_follow_referrals_checkbox = (By.CSS_SELECTOR, "input#follow_referrals")
    _ldap_basedn_field = (By.CSS_SELECTOR, "input#authentication_basedn")
    _ldap_binddn_field = (By.CSS_SELECTOR, "input#authentication_bind_dn")
    _ldap_bind_passwd_field = (By.CSS_SELECTOR, "input#authentication_bind_pwd")
    _ldap_validate_button = (By.CSS_SELECTOR, "img[alt='Validate the LDAP Settings by binding with the Host']")

    _aws_iam_accesskey_field = (By.CSS_SELECTOR, "input#authentication_amazon_key")
    _aws_iam_secretkey_field = (By.CSS_SELECTOR, "input#authentication_amazon_secret")
    _aws_iam_get_groups_checkbox = (By.CSS_SELECTOR, "input#amazon_role")
    _aws_iam_validate_button = (By.CSS_SELECTOR, "img[alt='Validate the Amazon Settings']")

    def save(self):
        self._wait_for_visible_element(*self._submit_button)
        self.selenium.find_element(*self._submit_button).click()
        self._wait_for_results_refresh()
        return AuthenticationSettingsTab(self.testsetup)

    def reset(self):
        self._wait_for_visible_element(*self._reset_button)
        self.selenium.find_element(*self._reset_button).click()
        self._wait_for_results_refresh()
        return AuthenticationSettingsTab(self.testsetup)

    def toggle_checkbox(self, state, *element):
        checkbox = self.selenium.find_element(*element)
        if state:
            if not checkbox.is_selected():
                return checkbox.click()
        else:
            if checkbox.is_selected():
                return checkbox.click()

    @property
    def current_auth_mode(self):
        return self.selenium.find_element(*self._auth_mode_selector).get_attribute("value")

    def validate(self):
        if (self.current_auth_mode in ("ldap", "ldaps")):
            validate_button = self._ldap_validate_button
        elif (self.current_auth_mode == "amazon"):
            validate_button = self._aws_iam_validate_button
        else:
            raise Exception("Unknown authentication mode selected")
        self._wait_for_visible_element(*validate_button)
        self.selenium.find_element(*validate_button).click()
        self._wait_for_results_refresh()
        return AuthenticationSettingsTab(self.testsetup)

    def ldap_server_fill_data(self,
                              hostname1="",
                              user_suffix="",
                              base_dn="",
                              bind_dn="",
                              bind_passwd="",
                              session_timeout_hours="1",
                              session_timeout_mins="0",
                              mode="ldap",
                              hostname2=None,
                              hostname3=None,
                              port="389",
                              user_type="userprincipalname",
                              get_groups=True,
                              get_roles=True,
                              follow_referrals=False):
        self.select_dropdown_by_value(session_timeout_hours, *self._session_timeout_hours_selector)
        self.select_dropdown_by_value(session_timeout_mins, *self._session_timeout_mins_selector)
        self.select_dropdown_by_value(mode, *self._auth_mode_selector)
        self._wait_for_results_refresh()
        if mode != "database":
            self._wait_for_visible_element(*self._ldap_host1_field)
            self.fill_field_by_locator(hostname1, *self._ldap_host1_field)
            if hostname2:
                self.fill_field_by_locator(hostname2, *self._ldap_host2_field)
            if hostname3:
                self.fill_field_by_locator(hostname3, *self._ldap_host3_field)
            self.fill_field_by_locator(port, *self._ldap_port_field)
            self.select_dropdown_by_value(user_type, *self._ldap_usertype_selector)
            self.fill_field_by_locator_with_wait(user_suffix, *self._ldap_usersuffix_field)
            self.toggle_checkbox(get_groups, *self._ldap_get_groups_checkbox)
            if get_groups:
                self._wait_for_visible_element(*self._ldap_follow_referrals_checkbox)
                self.toggle_checkbox(get_roles, *self._ldap_get_roles_forest_checkbox)
                self.toggle_checkbox(follow_referrals, *self._ldap_follow_referrals_checkbox)
                self.fill_field_by_locator(base_dn, *self._ldap_basedn_field)
                self.fill_field_by_locator(bind_dn, *self._ldap_binddn_field)
                self.fill_field_by_locator_with_wait(bind_passwd, *self._ldap_bind_passwd_field)
                self._wait_for_results_refresh()

    def aws_iam_fill_data(self,
                          session_timeout_hours="1",
                          session_timeout_mins="0",
                          mode="amazon",
                          access_key="",
                          secret_key="",
                          get_groups=True):
        self.select_dropdown_by_value(session_timeout_hours, *self._session_timeout_hours_selector)
        self.select_dropdown_by_value(session_timeout_mins, *self._session_timeout_mins_selector)
        self.select_dropdown_by_value(mode, *self._auth_mode_selector)
        self._wait_for_results_refresh()
        if mode != "database":
            self._wait_for_visible_element(*self._aws_iam_accesskey_field)
            self.fill_field_by_locator(access_key, *self._aws_iam_accesskey_field)
            self.fill_field_by_locator(secret_key, *self._aws_iam_secretkey_field)
            if get_groups:
                self._wait_for_visible_element(*self._aws_iam_get_groups_checkbox)
                self.toggle_checkbox(get_groups, *self._aws_iam_get_groups_checkbox)
