"""Provides functions to login as any user

Also provides a convenience function for logging in as admin using
the credentials in the cfme yamls.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the login page
"""

from selenium.webdriver.common.keys import Keys

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
from cfme.web_ui import Region, Form, fill
from utils import conf
from utils.log import logger


page = Region(title="CloudForms Management Engine: Dashboard",
    locators={
        'username': '//input[@id="user_name"]',
        'password': '//input[@id="user_password"]',
        'submit_button': '//a[@id="login"]',
        # Login page has an abnormal flash div
        'flash': '//div[@id="flash_div"]',
        'user_dropdown': '//div[@id="page_header_div"]//li[contains(@class, "dropdown")]',
        'logout': '//a[contains(@href, "/logout")]',
    },
    identifying_loc='username')

_form_fields = ('username', 'password', 'submit_button')
form = Form(fields=[loc for loc in page.locators.items() if loc[0] in _form_fields],
    identifying_loc='username')


def _click_on_login():
    """
    Convenience internal function to click the login locator submit button.
    """
    sel.click(page.submit_button)


def logged_in():
    if sel.is_displayed(page.user_dropdown):
        return True


def press_enter_after_password():
    """
    Convenience function to send a carriange return at the end of the password field.
    """
    sel.send_keys(page.password, Keys.RETURN)


def login(username, password, submit_method=_click_on_login):
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
    if not logged_in():
        # workaround for strange bug where we are logged out
        # as soon as we click something on the dashboard
        sel.sleep(1.0)

        logger.debug('Logging in as user %s' % username)
        fill(form, {'username': username, 'password': password})
        submit_method()
        flash.assert_no_errors()


def force_login_user(*args, **kwargs):
    """
    Force login to CFME using valid username and password; log out if already logged in.

    Args:
        args: A list of arguments to supply to the :py:meth:`login` method.
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.

    Warning:
        Use only with valid credentials.
    """
    if logged_in():
        logout()
    login(*args, **kwargs)


def login_admin(**kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.

    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    if current_username() != 'Administrator':
        logout()

    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    login(username, password, **kwargs)


def logout():
    """
    Logs out of CFME.
    """
    if logged_in():
        if not sel.is_displayed(page.logout):
            sel.click(page.user_dropdown)
        sel.click(page.logout)


def current_username():
    """ Returns the current username.

    Returns: the current username.
    """
    if logged_in():
        return sel.text(page.user_dropdown).split('|')[0].strip()
    else:
        return None
