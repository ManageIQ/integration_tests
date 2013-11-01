from pages.base import Base
from selenium.webdriver.common.by import By
from pages.regions.taskbar.taskbar import TaskbarMixin
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait


class CollectLogsTab(Base, TaskbarMixin):
    """ Configure
        Configuration
        Diagnostics accordion
        Collect Logs

    Getting and setting settings of the log depots, initiating logs.
    """
    _page_title = 'CloudForms Management Engine: Configuration'
    _edit_button_locator = (By.CSS_SELECTOR,
            "div.dhx_toolbar_btn[title='Edit the Log Depot settings for the selected Server']")
    _collect_button_locator = (By.CSS_SELECTOR, "div.dhx_toolbar_btn[title='Collect Logs']")
    _collect_current_logs_locator = (By.CSS_SELECTOR,
            "tr[title='Collect the current logs from the selected Server']\
                    >td.td_btn_txt>div.btn_sel_text")
    _collect_all_logs_locator = (By.CSS_SELECTOR,
            "tr[title='Collect all logs from the selected Server']\
                    >td.td_btn_txt>div.btn_sel_text")

    # Main table
    _log_depot_uri_locator = (By.XPATH,
                              "//*[@id='selected_div']/fieldset/table/tbody/tr[3]/td[2]")
    _server_locator = (By.XPATH,
                       "//*[@id='selected_div']/fieldset/table/tbody/tr[1]/td[3]")
    _server_status_locator = (By.XPATH,
                              "//*[@id='selected_div']/fieldset/table/tbody/tr[2]/td[2]")
    _last_log_collection_locator = (By.XPATH,
                                    "//*[@id='selected_div']/fieldset/table/tbody/tr[4]/td[2]")
    _last_message_locator = (By.XPATH,
                             "//*[@id='selected_div']/fieldset/table/tbody/tr[5]/td[2]")

    def wait_for(self, fun, time=15):
        """ Wrapper for WebDriverWait

        """
        return WebDriverWait(self.selenium, time).until(fun)

    @property
    def depot_uri(self):
        """ This returns the text with actual state of depot.

        If no depot configured, N/A is returned
        """
        return self.selenium.find_element(*self._log_depot_uri_locator).text.strip()

    @property
    def is_depot_configured(self):
        """ Returns bool whether is depot configured.

        If it is not configured, Depot URI shows N/A
        """
        return self.depot_uri != "N/A"

    @property
    def server(self):
        """ This returns the text with server name.

        """
        return self.selenium.find_element(*self._server_locator).text.strip()

    @property
    def server_status(self):
        """ This returns the text with server status.

        """
        return self.selenium.find_element(*self._server_status_locator).text.strip()

    @property
    def last_log_collection(self):
        """ This returns the text with the time of last log collection.

        """
        return self.selenium.find_element(*self._last_log_collection_locator).text.strip()

    @property
    def last_message(self):
        """ This returns the text with last message.

        """
        return self.selenium.find_element(*self._last_message_locator).text.strip()

    @property
    def edit_button(self):
        return self.selenium.find_element(*self._edit_button_locator)

    @property
    def collect_button(self):
        return self.selenium.find_element(*self._collect_button_locator)

    @property
    def collect_current_logs_button(self):
        return self.selenium.find_element(*self._collect_current_logs_locator)

    @property
    def collect_all_logs_button(self):
        return self.selenium.find_element(*self._collect_all_logs_locator)

    def collect_current_logs(self):
        """ Action Collect / Collect current logs

        """
        assert self.is_depot_configured, "Depot must be configured first!"
        ActionChains(self.selenium)\
            .click(self.collect_button)\
            .click(self.collect_current_logs_button)\
            .perform()
        self._wait_for_results_refresh()
        return "has been initiated" in self.flash.message

    def collect_all_logs(self):
        """ Action Collect / Collect all logs

        """
        assert self.is_depot_configured != "N/A", "Depot must be configured first!"
        ActionChains(self.selenium)\
            .click(self.collect_button)\
            .click(self.collect_all_logs_button)\
            .perform()
        self._wait_for_results_refresh()
        return "has been initiated" in self.flash.message

    def edit(self):
        """ Open the Edit page.

        """
        self.edit_button.click()
        self._wait_for_results_refresh()
        return self.EditLogDepotTab(self.testsetup)

    class EditLogDepotTab(Base):
        _page_title = 'CloudForms Management Engine: Configuration'

        _uri_text_locator = (By.XPATH,
                             "//*[@id='form_filter_div']/fieldset/table/tbody/tr[2]/td[2]")
        _type_selector_locator = (By.XPATH, "//*[@id='log_protocol']")
        _uri_field_locator = (By.XPATH, "//*[@id='uri']")
        _userid_field_locator = (By.XPATH, "//*[@id='log_userid']")
        _password_field_locator = (By.XPATH, "//*[@id='log_password']")
        _verify_password_field_locator = (By.XPATH, "//*[@id='log_verify']")
        _validate_locator = (By.XPATH, "//*[@id='val']")
        _save_locator = (By.XPATH, "//img[@title='Save Changes']")

        # The dropdown menu choices
        _types = {"nfs": "Network File System",
                  "ftp": "File Transfer Protocol",
                  "smb": "Samba",
                  None: "<No Depot>"}

        def wait_for(self, fun, time=15):
            """ Wrapper for WebDriverWait

            """
            return WebDriverWait(self.selenium, time).until(fun)

        @property
        def type_selector(self):
            return self.selenium.find_element(*self._type_selector_locator)

        @property
        def uri_field(self):
            return self.selenium.find_element(*self._uri_field_locator)

        @property
        def uri_text(self):
            return self.selenium.find_element(*self._uri_text_locator)

        @property
        def password_field(self):
            return self.selenium.find_element(*self._password_field_locator)

        @property
        def verify_password_field(self):
            return self.selenium.find_element(*self._verify_password_field_locator)

        @property
        def userid_field(self):
            return self.selenium.find_element(*self._userid_field_locator)

        @property
        def validate_button(self):
            return self.selenium.find_element(*self._validate_locator)

        @property
        def save_button(self):
            return self.selenium.find_element(*self._save_locator)

        def validate_credentials(self):
            """ Credential validation.

            If Validate button is present, then it's clicked on it after it appears visible.
            Then validity of the credentials is verified against a flash message.
            """
            if not self.validate_button:
                return True     # NFS does not have any credentials
            self._wait_for_visible_element(*self._validate_locator)
            self.validate_button.click()
            self._wait_for_results_refresh()
            return "Log Depot Settings successfuly validated" in self.flash.message

        @property
        def depot_type(self):
            """ Getter for the dropdown menu with depot types


            """
            t = self.type_selector.text.strip()
            for abbr, full in self._types.iteritems():
                if full == t:
                    return abbr
            raise Exception("Error when getting depot type!!!")

        @depot_type.setter
        def depot_type(self, value):
            """ Setter for the dropdown menu with depot types

            It verifies whether the parameter is correct, it then finds the correct item,
            clicks it and waits until form has changed appropriately.
            """
            assert value in self._types.keys(), "depot type must be one of %s." %\
                ", ".join([str(t) for t in self._types])
            look_for = self._types[value]
            for option in self.type_selector.find_elements_by_tag_name("option"):
                if option.text.strip() == look_for:
                    option.click()
            # Wait for correct form to appear
            # URI text must appear if some depot type is selected
            if value:
                self.wait_for(lambda x: self.uri_text)
                # URI text must start with the look_for
                self.wait_for(lambda x: self.uri_text.text.strip().startswith(value))
            else:
                # Wait for form to disappear (Validate button disappears)
                self.wait_for(lambda x: not self.is_element_visible(*self._validate_locator))

        def fill_credentials(self, depot_type, uri,
                             user=None,
                             password=None,
                             ignore_validation=False):
            """ Fills in and validates the credentials.

            The validation is not done for NFS as it does not have a Validate button.
            """
            assert depot_type and depot_type in self._types.keys()
            self.depot_type = depot_type
            self.fill_field_element(uri, self.uri_field)
            if depot_type in ["smb", "ftp"]:
                assert user, "You must specify a username for smb or ftp"
                assert password, "You must specify a password for smb or ftp"
                self.fill_field_element(user, self.userid_field)
                self.fill_field_element(password, self.password_field)
                self.fill_field_element(password, self.verify_password_field)
                return ignore_validation or self.validate_credentials()
            return True

        def save_settings(self):
            """ Save settings

            Saves the settings and returns boolean whether it succeeded.
            """
            self.save_button.click()
            self._wait_for_results_refresh()
            return "Log Depot Settings were saved" in self.flash.message
