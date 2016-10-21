from __future__ import absolute_import

from navmazing import NavigateToSibling

from . import Server
from utils.appliance import ViaUI

from cfme import BaseLoggedInPage
from cfme.dashboard import DashboardView

from utils.appliance.implementations.ui import navigator, CFMENavigateStep

import time
from selenium.webdriver.common.keys import Keys

from cfme import Credential
from utils import conf
from utils.log import logger

from widgetastic.widget import Text, View
from widgetastic_patternfly import Button, Input, FlashMessages


@Server.address.external_implementation_for(ViaUI)
def address(self):
    print "USING UI ADDRESS"
    return 'https://{}/'.format(self.appliance.address)


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


@Server.logged_in.external_implementation_for(ViaUI)
def logged_in(self):
    return self.appliance.browser.create_view(BaseLoggedInPage).logged_in


LOGIN_METHODS = ['click_on_login', 'press_enter_after_password', '_js_auth_fn']


@Server.login.external_implementation_for(ViaUI)
def login(self, user=None, submit_method=LOGIN_METHODS[-1]):
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
    from utils.appliance.endpoints.ui import navigate_to
    navigate_to(self.appliance.server, 'LoginScreen')

    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        from cfme.configure.access_control import User
        user = User(credential=cred)

    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)

    if not logged_in_view.logged_in_as_user(user):
        if logged_in_view.logged_in:
            logged_in_view.logout()

        time.sleep(1)

        logger.debug('Logging in as user %s', user.credential.principal)
        login_view = self.appliance.browser.create_view(LoginPage)

        login_view.log_in(user.credential.principal, user.credential.secret, method=submit_method)
        logged_in_view.flush_widget_cache()
        user.name = logged_in_view.current_fullname
        assert logged_in_view.logged_in_as_user
        logged_in_view.flash.assert_no_error()
        self.appliance.user = user


@Server.login_admin.external_implementation_for(ViaUI)
def login_admin(self, **kwargs):
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
    self.login(user, **kwargs)


@Server.logout.external_implementation_for(ViaUI)
def logout(self):
    """
    Logs out of CFME.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        logged_in_view.logout()
        self.appliance.user = None


@Server.current_full_name.external_implementation_for(ViaUI)
def current_full_name(self):
    """ Returns the current username.

    Returns: the current username.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        return logged_in_view.current_fullname
    else:
        return None


@navigator.register(Server)
class LoginScreen(CFMENavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from utils.browser import ensure_browser_open
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self):
        # Can be either blank or logged in
        from utils.browser import ensure_browser_open
        logged_in_view = self.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            logged_in_view.logout()
        if not self.view.is_displayed:
            # Something is wrong
            del self.view  # In order to unbind the browser
            quit()
            ensure_browser_open(self.obj.appliance.server.address())
            if not self.view.is_displayed:
                raise Exception('Could not open the login screen')


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    VIEW = BaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def step(self):
        login_view = self.create_view(LoginPage)
        login_view.log_in(self.obj.appliance.user)


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_top_right
            click_top_right('Configuration')
        else:
            from cfme.web_ui.menu import nav
            nav._nav_to_fn('Settings', 'Configuration')(None)


@navigator.register(Server)
class Dashboard(CFMENavigateStep):
    VIEW = DashboardView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select('Cloud Intel', 'Dashboard')
