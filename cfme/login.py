"""Provides functions to login as any user

Also provides a convenience function for logging in as admin using
the credentials in the cfme yamls.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the login page
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import cfme.fixtures.pytest_selenium as browser
import cfme.web_ui.flash as flash
from cfme.web_ui import Region
from utils import conf
from utils.log import logger


page = Region(title="CloudForms Management Engine: Dashboard",
              locators={"username_text": (By.CSS_SELECTOR, '#user_name'),
                        "password_text": (By.CSS_SELECTOR, '#user_password'),
                        "submit_button": (By.ID, 'login'),
                        "logout": (By.CSS_SELECTOR, 'a[href="/dashboard/logout"]'),
                        "user_dropdown": (By.CSS_SELECTOR, "div#page_header_div li.dropdown")},
              identifying_loc="username_text")


def _click_on_login():
    """
    Convenience internal function to click the login locator submit button.
    """
    browser.click(page.submit_button)


def _is_logged_in():
        if browser.is_displayed(page.user_dropdown):
            return True


def press_enter_after_password():
    """
    Convenience function to send a carriange return at the end of the password field.
    """
    browser.send_keys(page.password_text, Keys.RETURN)


def login(user, password, submit_method=_click_on_login):
    """
    Login to CFME with the given username and password.
    Optionally, submit_method can be press_enter_after_password
    to use the enter key to login, rather than clicking the button.

    Args:
        user: The username to fill in the username field.
        password: The password to fill in the password field.
        submit_method: A function to call after the username and password have been input.

    Raises:
        RuntimeError: If the login fails, ie. if a flash message appears
    """
    # TODO: Should probably do the username check here, but there are pretty usernames to deal with
    # e.g. 'admin' shows up in the UI as 'Administrator'
    if not _is_logged_in():
        # workaround for strange bug where we are logged out
        # as soon as we click something on the dashboard
        browser.sleep(1.0)

        logger.debug('Logging in as user %s' % user)
        browser.set_text(page.username_text, user)
        browser.set_text(page.password_text, password)
        submit_method()
        flash.assert_no_errors()


def login_admin(**kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.

    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    if current_username() != 'Administrator':
        logout()

    user = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    login(user, password, **kwargs)


def logout():
    """
    Logs out of CFME.
    """
    if _is_logged_in():
        if not browser.is_displayed(page.logout):
            browser.click(page.user_dropdown)
        browser.click(page.logout)


def current_username():
    """ Returns the current username.

    Returns: the current username.
    """
    if _is_logged_in():
        return browser.text(page.user_dropdown).split('|')[0].strip()
    else:
        return None
