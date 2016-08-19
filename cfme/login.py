"""Provides functions to login as any user

Also provides a convenience function for logging in as admin using
the credentials in the cfme yamls.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the login page
"""
from __future__ import absolute_import

from functools import wraps
from selenium.webdriver.common.keys import Keys

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
from cfme import Credential
from cfme.configure.access_control import User
from cfme.web_ui import Region
from utils import conf, version
from utils.browser import ensure_browser_open, quit
from utils.log import logger
from fixtures.pytest_store import store

from utils.appliance import current_appliance

from selenium_view import View, Input, Button, Text
from . import BasicLoggedInView


class LoginPage(View):
    username = Input('user_name')
    password = Input('user_password')
    submit = Button('Login')
    update = Text('//a[normalize-space(@title)="Update Password"]')
    back = Text('//a[normalize-space(@title)="Back"]')
    user_new_password = Input('user_new_password')
    user_verify_password = Input('user_verify_password')

    # Details
    region = Text(
        '//div[contains(@class, "container")]//div[contains(@class, "details")]'
        '/p[normalize-space(text())="Region:"]/span')
    zone = Text(
        '//div[contains(@class, "container")]//div[contains(@class, "details")]'
        '/p[normalize-space(text())="Zone:"]/span')
    appliance_name = Text(
        '//div[contains(@class, "container")]//div[contains(@class, "details")]'
        '/p[normalize-space(text())="Appliance:"]/span')

    @property
    def is_displayed(self):
        return self.submit.is_displayed

    @property
    def logged_out(self):
        login_w = [self.username, self.password, self.submit, self.update]
        change_w = [
            self.back, self.username, self.password, self.user_new_password,
            self.user_verify_password]
        return all(w.is_displayed for w in login_w) or all(w.is_displayed for w in change_w)

    @property
    def logged_in(self):
        return not self.logged_out

    def show_password_update_form(self):
        """ Shows the password update form """
        if self.update.is_displayed:
            self.update()

    def close_password_update_form(self):
        """ Goes back to main login form on login page """
        if not self.update.is_displayed:
            self.back()

    def update_password(
            self, username, password, new_password, verify_password=None,
            submit_method=None):
        """ Changes user password """
        self.show_password_update_form()
        submit_method = submit_method or click_on_login
        self.fill({
            'username': username,
            'password': password,
            'user_new_password': new_password,
            'user_verify_password': verify_password if verify_password is not None else new_password
        })
        submit_method(self)

    def clear_fields(self):
        self.show_password_update_form()
        self.fill({
            'username': '',
            'password': '',
            'user_new_password': '',
            'user_verify_password': '',
        })


def login_shim(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
        return f(login_page, *args, **kwargs)

    return wrapped

page = Region(
    # TODO: Make title defer it's resolution
    title={version.LOWEST: "Dashboard", '5.5': "Login"},
    locators={
        # Login page has an abnormal flash div
        'flash': '//div[@id="flash_div"]',
    },
    identifying_loc='submit_button')


def click_on_login(login_page):
    """
    Convenience internal function to click the login locator submit button.
    """
    login_page.submit()


def _js_auth_fn(login_page):
    # In case clicking on login or hitting enter is broken, this can still let you log in
    # This shouldn't be used in automation, though.
    login_page.browser.execute_script('miqAjaxAuth();')


def press_enter_after_password(login_page):
    """
    Convenience function to send a carriange return at the end of the password field.
    """
    login_page.browser.send_keys(login_page.password, Keys.RETURN)


@login_shim
def logged_in(login_page):
    return login_page.logged_in


LOGIN_METHODS = [click_on_login, press_enter_after_password]


def login(user, submit_method=_js_auth_fn):
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

    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)

    if not logged_in() or user.credential.principal is not current_username():
        if logged_in():
            logout()
        # workaround for strange bug where we are logged out
        # as soon as we click something on the dashboard
        sel.sleep(1.0)

        logger.debug('Logging in as user %s', user.credential.principal)
        login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
        try:
            login_page.fill({
                'username': user.credential.principal,
                'password': user.credential.secret,
            })
        except sel.InvalidElementStateException as e:
            logger.warning("Got an error. Details follow.")
            msg = str(e).lower()
            if "element is read-only" in msg:
                logger.warning("Got a read-only login form, will reload the browser.")
                # Reload browser
                quit()
                ensure_browser_open()
                sel.sleep(1.0)
                sel.wait_for_ajax()
                # And try filling the form again
                login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
                login_page.fill({
                    'username': user.credential.principal,
                    'password': user.credential.secret,
                })
            else:
                logger.warning("Unknown error, reraising.")
                logger.exception(e)
                raise
        with sel.ajax_timeout(90):
            submit_method(login_page)
        flash.assert_no_errors()
        user.full_name = _full_name()
        store.user = user


def login_admin(**kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.

    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    if current_full_name() != 'Administrator':
        logout()

        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)
        login(user, **kwargs)


def logout():
    """
    Logs out of CFME.
    """
    if logged_in():
        logged_in_view = current_appliance.browser.open_view(BasicLoggedInView, navigate=False)
        if not logged_in_view.logout.is_displayed:
            logged_in_view.user_dropdown.click()
        logged_in_view.logout()
        logged_in_view.browser.handle_alert(wait=False)
        store.user = None


def _full_name():
    logged_in_view = current_appliance.browser.open_view(BasicLoggedInView, navigate=False)
    return logged_in_view.user_dropdown.read().split('|')[0].strip()


def current_full_name():
    """ Returns the current username.

    Returns: the current username.
    """
    if logged_in():
        return _full_name()
    else:
        return None


def current_user():
    return store.user


def current_username():
    u = current_user()
    return u and u.credential.principal


def fill_login_fields(username, password):
    """ Fills in login information without submitting the form """
    if logged_in():
        logout()
    login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
    login_page.fill({
        'username': username,
        'password': password,
    })


def show_password_update_form():
    """ Shows the password update form """
    if logged_in():
        logout()
    login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
    return login_page.show_password_update_form()


def update_password(username, password, new_password,
                    verify_password=None, submit_method=click_on_login):
    """ Changes user password """
    if logged_in():
        logout()
    login_page = current_appliance.browser.open_view(LoginPage, navigate=False)
    login_page.update_password(username, password, new_password, verify_password, submit_method)


@login_shim
def close_password_update_form(login_page):
    """ Goes back to main login form on login page """
    login_page.close_password_update_form()


@login_shim
def clear_fields(login_page):
    """ clears all form fields """
    login_page.clear_fields()
