#!/usr/bin/env python
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import cfme.fixtures.pytest_selenium as browser
from cfme.web_ui import Region
from utils import conf
import cfme.web_ui.flash as flash

page = Region(title="CloudForms Management Engine: Dashboard",
              locators={"username_text": (By.CSS_SELECTOR, '#user_name'),
                        "password_text": (By.CSS_SELECTOR, '#user_password'),
                        "submit_button": (By.ID, 'login')},
              identifying_loc="username_text")


def _click_on_login():
    browser.click(page.submit_button)


def press_enter_after_password():
    browser.send_keys(page.password_text, Keys.RETURN)


def login(user, password, submit_method=_click_on_login):
    '''
    Login to CFME with the given username and password.
    Optionally, submit_method can be press_enter_after_password
    to use the enter key to login, rather than clicking the button.
    '''
    browser.set_text(page.username_text, user)
    browser.set_text(page.password_text, password)
    submit_method()
    login_error = flash.get_message()
    if login_error:
        raise RuntimeError("Login as %s:%s failed: '%s'" % (user, password, login_error))


def login_admin(**kwargs):
    user = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    login(user, password, **kwargs)
