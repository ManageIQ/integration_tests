#!/usr/bin/env python
from selenium.webdriver.common.by import By

from base import Base
from page import Page

class LoginPage(Base):

    _login_username_field_locator = (By.CSS_SELECTOR, '#user_name')
    _login_password_field_locator = (By.CSS_SELECTOR, '#user_password')
    _login_submit_button_locator = (By.CSS_SELECTOR, '#login')

    # Demo locators
    #_page_title = u"Mozilla \u2014 Home of the Mozilla Project \u2014 mozilla.org"
    #_header_locator = (By.CSS_SELECTOR, 'h1')

    @property
    def username(self):
        return self.selenium.find_element(*self._username)

    @property
    def password(self):
        return self.selenium.find_element(*self._password)

    @property
    def login_button(self):
        return self.selenium.find_element(*self._login_button)

    @property
    def elements_count(self):
        return len(self.selenium.find_elements(*self._username))

    def click_on_login_button(self):
        self.selenium.find_element(*self._login_button).click()

    def login(self, user='default'):
        credentials = self.testsetup.credentials[user]
        self.selenium.find_element(*self._login_username_field_locator).send_keys(credentials['username'])
        self.selenium.find_element(*self._login_password_field_locator).send_keys(credentials['password'])
        self.selenium.find_element(*self._login_submit_button_locator).click()
        from pages.dashboard_page import DashboardPage
        return DashboardPage(self.testsetup)

