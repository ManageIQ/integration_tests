import time

from navmazing import NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import FlashMessages
from widgetastic_patternfly import Input
from widgetastic_patternfly import NavDropdown
from widgetastic_patternfly import Text
from widgetastic_patternfly.utils import PFIcon

from cfme.base import Server
from cfme.base.credential import Credential
from cfme.utils import conf
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ssui import navigate_to
from cfme.utils.appliance.implementations.ssui import navigator
from cfme.utils.appliance.implementations.ssui import SSUINavigateStep
from cfme.utils.browser import ensure_browser_open
from cfme.utils.browser import quit
from cfme.utils.log import logger
from widgetastic_manageiq import SSUIVerticalNavigation


class SSUISettingsNavDropdown(NavDropdown):
    """iuser pficon-user to differentiate from help menu"""
    ROOT = ('//nav'
            '//li[.//a[contains(@class, "dropdown-toggle") and '
            './/i[contains(@class, "{}")]] '
            'and contains(@class, "dropdown")]'.format(PFIcon.icons.USER))


class SSUIHelpNavDropdown(NavDropdown):
    ROOT = '//nav//li[@ng-if="vm.permissions.helpMenu"]'


class SSUIBaseLoggedInPage(View):
    """This page should be subclassed by any page that models any other page that is available as
    logged in.
    """
    flash = View.nested(FlashMessages)
    # TODO don't use `help` here, its a built-in
    help = SSUIHelpNavDropdown()
    navigation = SSUIVerticalNavigation('//ul[@class="list-group"]')
    domain_switcher = Button(id="domain-switcher")
    shopping_cart = Text('.//li/a[@title="Shopping cart"]')
    settings = SSUISettingsNavDropdown()

    @property
    def is_displayed(self):
        return self.logged_in_as_current_user

    def logged_in_as_user(self, user):
        if self.logged_out:
            return False
        return user.name == self.current_fullname

    @property
    def logged_in_as_current_user(self):
        return self.logged_in_as_user(self.extra.appliance.user)

    # TODO remove this property, it is erroneous. View properties should be returning data from UI
    @property
    def current_username(self):
        try:
            return self.extra.appliance.user.principal
        except AttributeError:
            return None

    @property
    def current_fullname(self):
        return self.settings.text

    @property
    def logged_in(self):
        return (
            self.settings.is_displayed and
            self.shopping_cart.is_displayed)

    @property
    def logged_out(self):
        return not self.logged_in

    def logout(self):
        self.settings.select_item('Logout')
        self.browser.handle_alert(wait=None)
        self.extra.appliance.user = None


class LoginPage(View):
    flash = View.nested(FlashMessages)
    username = Input(id='inputUsername')
    password = Input(id='inputPassword')
    login = Button('Log In')

    def submit_login(self, method='click_on_login'):
        if method == 'click_on_login':
            self.login.click()
        elif method == 'press_enter_after_password':
            self.browser.send_keys(Keys.ENTER, self.password)
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
        logged_in_view = self.browser.create_view(SSUIBaseLoggedInPage)
        if logged_in_view.logged_in:
            if user.name is None:
                name = logged_in_view.current_fullname
                self.logger.info(
                    'setting the appliance.user.name to %r because it was not specified', name)
                user.name = name
            self.extra.appliance.user = user


@MiqImplementationContext.external_for(Server.address, ViaSSUI)
def address(self):
    logger.info("USING SSUI ADDRESS")
    return self.appliance.url_path('/self_service/')


LOGIN_METHODS = ['click_on_login', 'press_enter_after_password']


@MiqImplementationContext.external_for(Server.login, ViaSSUI)
def login(self, user=None, method=LOGIN_METHODS[-1]):
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = self.appliance.collections.users.instantiate(credential=cred)

    logged_in_view = self.appliance.ssui.create_view(SSUIBaseLoggedInPage)

    if logged_in_view.logged_in_as_user(user):
        return

    if logged_in_view.logged_in:
        logged_in_view.logout()

    login_view = navigate_to(self.appliance.server, 'LoginScreen')
    login_view.log_in(user, method=method)
    # Without this the login screen just exits after logging in
    time.sleep(3)
    login_view.flash.assert_no_error()
    self.browser.plugin.ensure_page_safe()
    logged_in_view.wait_displayed('10s')
    return logged_in_view


@MiqImplementationContext.external_for(Server.login_admin, ViaSSUI)
def login_admin(self, **kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.
    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    cred = Credential(principal=username, secret=password)
    user = self.appliance.collections.users.instantiate(credential=cred)
    user.name = 'Administrator'
    logged_in_view = self.login(user, **kwargs)
    return logged_in_view


@navigator.register(Server)
class LoggedIn(SSUINavigateStep):
    VIEW = SSUIBaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def step(self, *args, **kwargs):
        with self.obj.appliance.context.use(ViaSSUI):
            self.obj.login()


@navigator.register(Server)
class LoginScreen(SSUINavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self, *args, **kwargs):
        # Can be either blank or logged in
        del self.view  # In order to unbind the browser
        quit()
        ensure_browser_open(self.obj.appliance.server.address())
        if not self.view.is_displayed:
            raise Exception('Could not open the login screen')
