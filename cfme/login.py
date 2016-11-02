"""Provides functions to login as any user

Also provides a convenience function for logging in as admin using
the credentials in the cfme yamls.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the login page
"""
from __future__ import absolute_import

import time
from selenium.webdriver.common.keys import Keys

from cfme import Credential
from utils import conf
from utils.log import logger
from fixtures.pytest_store import store

from widgetastic.widget import Text, View
from widgetastic_patternfly import Button, Input, FlashMessages

from . import BaseLoggedInPage


class LoginPage(View):
    flash = FlashMessages('div#flash_text_div')

    class details(View):  # noqa
        region = Text('.//p[normalize-space(text())="Region:"]/span')
        zone = Text('.//p[normalize-space(text())="Zone:"]/span')
        appliance = Text('.//p[normalize-space(text())="Appliance:"]/span')

    change_password = Text('.//a[normalize-space(.)="Update password"]')
    back = Text('.//a[normalize-space(.)="Back"]')
    username = Input(name='user_name')
    password = Input(name='user_password')
    new_password = Input(name='user_new_password')
    verify_password = Input(name='user_verify_password')
    login = Button('Login')

    def show_update_password(self):
        if not self.new_password.is_displayed:
            self.change_password.click()

    def hide_update_password(self):
        if self.new_password.is_displayed:
            self.back.click()

    def login_admin(self, **kwargs):
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        from cfme.configure.access_control import User
        user = User(credential=cred, name='Administrator')
        return self.log_in(user, **kwargs)

    def submit_login(self, method='click_on_login'):
        if method == 'click_on_login':
            self.login.click()
        elif method == 'press_enter_after_password':
            self.browser.send_keys(Keys.ENTER, self.password)
        elif method == '_js_auth_fn':
            self.browser.execute_script('miqAjaxAuth();')
        else:
            raise ValueError('Unknown method {}'.format(method))
        if self.flash.is_displayed:
            self.flash.assert_no_error()

    def log_in(self, user, method='click_on_login'):
        self.fill({
            'username': user.credential.principal,
            'password': user.credential.secret,
        })
        self.submit_login(method)
        logged_in_view = self.browser.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in and user.name is None:
            name = logged_in_view.current_fullname
            self.logger.info(
                'setting the appliance.user.name to %r because it was not specified', name)
            user.name = name
        self.extra.appliance.user = user

    def update_password(
            self, username, password, new_password, verify_password=None,
            method='click_on_login'):
        self.show_update_password()
        self.fill({
            'username': username,
            'password': password,
            'new_password': new_password,
            'verify_password': verify_password if verify_password is not None else new_password
        })
        self.submit_login(method)

    def logged_in_as_user(self, user):
        return False

    @property
    def logged_in_as_current_user(self):
        return False

    @property
    def current_username(self):
        return None

    @property
    def current_fullname(self):
        return None

    @property
    def logged_in(self):
        return not self.logged_out

    @property
    def logged_out(self):
        return self.username.is_displayed and self.password.is_displayed and self.login.is_displayed

    @property
    def is_displayed(self):
        return self.logged_out


def logged_in():
    return store.current_appliance.browser.create_view(BaseLoggedInPage).logged_in


LOGIN_METHODS = ['click_on_login', 'press_enter_after_password', '_js_auth_fn']


def login(user, submit_method=LOGIN_METHODS[-1]):
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
    # Circular import
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        from cfme.configure.access_control import User
        user = User(credential=cred, name='Administrator')

    logged_in_view = store.current_appliance.browser.create_view(BaseLoggedInPage)

    if not logged_in_view.logged_in_as_user(user):
        if logged_in_view.logged_in:
            logged_in_view.logout()

        from utils.appliance.implementations.ui import navigate_to
        login_view = navigate_to(store.current_appliance.server, 'LoginScreen')

        time.sleep(1)

        logger.debug('Logging in as user %s', user.credential.principal)
        login_view.flush_widget_cache()

        login_view.log_in(user, method=submit_method)
        logged_in_view.flush_widget_cache()
        user.name = logged_in_view.current_fullname
        assert logged_in_view.logged_in_as_user
        logged_in_view.flash.assert_no_error()
        store.current_appliance.user = user


def login_admin(**kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.

    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    cred = Credential(principal=username, secret=password)
    from cfme.configure.access_control import User
    user = User(credential=cred)
    user.name = 'Administrator'
    login(user, **kwargs)


def logout():
    """
    Logs out of CFME.
    """
    logged_in_view = store.current_appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        logged_in_view.logout()
        store.current_appliance.user = None


def current_full_name():
    """ Returns the current username.

    Returns: the current username.
    """
    logged_in_view = store.current_appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        return logged_in_view.current_fullname
    else:
        return None


def current_user():
    return store.current_appliance.user
