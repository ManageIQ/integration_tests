from . import Server

from navmazing import NavigateToSibling
from widgetastic.widget import View, ParametrizedView
from widgetastic_patternfly import NavDropdown, FlashMessages, Input, Button
from widgetastic_manageiq import SSUIVerticalNavigation
from widgetastic.utils import ParametrizedLocator

from cfme.base.credential import Credential
from cfme.configure.access_control import User
from cfme.utils import conf
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ssui import navigator, SSUINavigateStep, navigate_to
from cfme.utils.browser import ensure_browser_open, quit
from cfme.utils.log import logger

import time


class SSUIBaseLoggedInPage(View):
    """This page should be subclassed by any page that models any other page that is available as
    logged in.
    """
    flash = FlashMessages('div#flash_text_div')
    help = NavDropdown('.//li[./a[@id="dropdownMenu1"]]')
    navigation = SSUIVerticalNavigation('//ul[@class="list-group"]')
    domain_switcher = Button(id="domain-switcher")

    @ParametrizedView.nested
    class settings(ParametrizedView):  # noqa
        PARAMETERS = ("user_name",)
        setting = NavDropdown(ParametrizedLocator('.//li[./a[@title={user_name|quote}]]'))

        def text(self):
            return self.setting.text

        def is_displayed(self):
            return self.setting.is_displayed

        def select_item(self, option):
            return self.setting.select_item(option)

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

    @property
    def current_username(self):
        try:
            return self.extra.appliance.user.principal
        except AttributeError:
            return None

    @property
    def current_fullname(self):
        return self.settings(self.extra.appliance.user.credential.principal).text()

    @property
    def logged_in(self):
        return (
            self.settings(self.extra.appliance.user.credential.principal).is_displayed() and
            self.domain_switcher.is_displayed)

    @property
    def logged_out(self):
        return not self.logged_in

    def logout(self):
        self.settings(self.extra.appliance.user.credential.principal).select_item('Logout')
        self.browser.handle_alert(wait=None)
        self.extra.appliance.user = None


class LoginPage(View):
    flash = FlashMessages('div#flash_text_div')
    username = Input(id='inputUsername')
    password = Input(id='inputPassword')
    login = Button('Log In')


@Server.address.external_implementation_for(ViaSSUI)
def address(self):
    logger.info("USING SSUI ADDRESS")
    return 'https://{}/self_service/'.format(self.appliance.address)


@Server.login.external_implementation_for(ViaSSUI)
def login(self, user=None, **kwargs):
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)

    logged_in_view = self.appliance.ssui.create_view(SSUIBaseLoggedInPage)

    if logged_in_view.logged_in_as_user(user):
        return

    if logged_in_view.logged_in:
        logged_in_view.logout()

    login_view = navigate_to(self.appliance.server, 'LoginScreen')
    login_view.fill({
        'username': user.credential.principal,
        'password': user.credential.secret,
    })
    login_view.login.click()
    # Without this the login screen just exits after logging in
    time.sleep(3)
    login_view.flash.assert_no_error()
    self.browser.plugin.ensure_page_safe()


@navigator.register(Server)
class LoggedIn(SSUINavigateStep):
    VIEW = SSUIBaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def step(self):
        with self.obj.appliance.context.use(ViaSSUI):
            self.obj.login()


@navigator.register(Server)
class LoginScreen(SSUINavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self):
        # Can be either blank or logged in
        del self.view  # In order to unbind the browser
        quit()
        ensure_browser_open(self.obj.appliance.server.address())
        if not self.view.is_displayed:
            raise Exception('Could not open the login screen')
