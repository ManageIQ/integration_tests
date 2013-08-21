# -*- coding: utf8 -*-
from selenium.webdriver.common.by import By
from pages.cloud.providers.common_form import AddFormCommon

# pylint: disable=R0904

class Edit(AddFormCommon):
    '''Edit Cloud Provider page'''
    _page_title = 'CloudForms Management Engine: Cloud Providers'
    _save_button_locator = (
            By.CSS_SELECTOR,
            "div#buttons_on > ul#form_buttons > li > img[title='Save Changes']")

    @property
    def save_button(self):
        '''Save button'''
        return self.get_element(*self._save_button_locator)

    def edit_provider(self, provider):
        '''Edit a provider given a provider dict'''
        for key, value in provider.iteritems():
            # Special cases
            if "server_zone" in key:
                if self.server_zone.tag_name == "select":
                    self.select_dropdown(value)
            elif "edit_name" in key:
                self.name.clear()
                self.name.send_keys(value)
            else:
                # Skip name
                if "name" in key:
                    continue
                # Only try to send keys if there is actually a property
                if hasattr(self, key):
                    attr = getattr(self, key)
                    attr.clear()
                    attr.send_keys(value)

            if "amqp_credentials" == key:
                self.click_on_amqp_credentials()
                credentials = self.testsetup.credentials[value]
                self.amqp_userid.clear()
                self.amqp_userid.send_keys(credentials['username'])
                self.amqp_password.clear()
                self.amqp_password.send_keys(credentials['password'])
                self.amqp_verify.clear()
                self.amqp_verify.send_keys(credentials['password'])
            elif "credentials" in key:
                credentials = self.testsetup.credentials[value]
                self.default_userid.clear()
                self.default_userid.send_keys(credentials['username'])
                self.default_password.clear()
                self.default_password.send_keys(credentials['password'])
                self.default_verify.clear()
                self.default_verify.send_keys(credentials['password'])

        self._wait_for_visible_element(*self._save_button_locator)
        return self.click_on_save()

    def click_on_save(self):
        '''Click on save button'''
        self.save_button.click()
        self._wait_for_results_refresh()
        from pages.cloud.providers.details import Detail
        return Detail(self.testsetup)
