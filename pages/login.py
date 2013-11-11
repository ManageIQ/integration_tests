#!/usr/bin/env python
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import fixtures.pytest_selenium as browser
from region import Region


login_page = Region(title="CloudForms Management Engine: Dashboard",
                    locators={"username_text": (By.CSS_SELECTOR, '#user_name'),
                              "password_text": (By.CSS_SELECTOR, '#user_password'),
                              "submit_button": (By.ID, 'login')},
                    identifying_loc="username_text")


def _click_on_login():
    browser.click(login_page.submit_button)


def press_enter_after_password():
    browser.send_keys(login_page.password_text, Keys.RETURN)


def login(user, password, submit_method=_click_on_login):
    '''
    Login to CFME with the given username and password.
    Optionally, submit_method can be press_enter_after_password
    to use the enter key to login, rather than clicking the button.
    '''
    browser.send_keys(login_page.username_text, user)
    browser.send_keys(login_page.password_text, password)
    submit_method()
