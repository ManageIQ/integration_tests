from pages.base import Base
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select


class AuthenticationSettingsTab(Base):
    _page_title = 'CloudForms Management Engine: Configuration'
    _submit_button = (By.CSS_SELECTOR, "img[title='Save Changes']")
    _reset_button = (By.CSS_SELECTOR, "img[title='Reset Changes']")

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

    _validate_button = (By.CSS_SELECTOR, "img[alt='Validate the LDAP Settings by binding with the Host']")

    def ldap_server_fill_data(self,
                              hostname1="",
                              user_suffix="",
                              base_dn="",
                              bind_dn="",
                              bind_passwd="",
                              session_timeout_hours="1",
                              session_timeout_mins="0",
                              mode="LDAP",
                              hostname2=None,
                              hostname3=None,
                              port="389",
                              user_type="User Principle Name",
                              get_groups=True,
                              get_roles=True,
                              follow_referrals=False):
        self.select_dropdown(session_timeout_hours, *self._session_timeout_hours_selector)
        self.select_dropdown(session_timeout_mins, *self._session_timeout_mins_selector)
        self.select_dropdown(mode, *self._auth_mode_selector)
        self.fill_field(hostname1, *self._ldap_host1_field)
        if hostname2:
            self.fill_field(hostname2, *self._ldap_host2_field)
        if hostname3:
            self.fill_field(hostname3, *self._ldap_host3_field)
        self.fill_field(port, *self._ldap_port_field)
        self.select_dropdown(user_type, *self._ldap_usertype_selector)
        self.fill_field(user_suffix, *self._ldap_usersuffix_field)
        self.toggle_checkbox(get_groups, *self._ldap_get_groups_checkbox)
        self.toggle_checkbox(get_roles, *self._ldap_get_roles_forest_checkbox)
        self.toggle_checkbox(follow_referrals, *self._ldap_follow_referrals_checkbox)
        self.fill_field(base_dn, *self._ldap_basedn_field)
        self.fill_field(bind_dn, *self._ldap_binddn_field)
        self.fill_field(bind_passwd, *self._ldap_bind_passwd_field)

    def fill_field(self, data, *element):
        field = self.selenium.find_element(*element)
        field.clear()
        return field.send_keys(data)

    def toggle_checkbox(self, state, *element):
        checkbox = self.selenium.find_element(*element)
        if state:
            if not checkbox.is_selected(): 
                return checkbox.click()
        else:
            if checkbox.is_selected():
                return checkbox.click()

    def validate(self):
        self._wait_for_visible_element(*self._validate_button)
        self.selenium.find_element(*self._validate_button).click()
        self._wait_for_results_refresh()
        return AuthenticationSettingsTab(self.testsetup)
