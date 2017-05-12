from selenium.common.exceptions import InvalidElementStateException

from . import Server
from utils.appliance import ViaSSUI
from utils.appliance.implementations.ssui import navigator, SSUINavigateStep, navigate_to

from cfme import Credential
from cfme.configure.access_control import User
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, fill
from widgetastic_patternfly import Input, Button
from utils import conf
from utils.browser import ensure_browser_open, quit
from utils.log import logger

from widgetastic.widget import View


class LoginPage(View):
    username = Input(id='inputUsername')
    password = Input(name='inputPassword')
    login = Button('Log In')


ssui_form = Form(
    fields=[('username', '//div[@class="form-group"]//input[@id="inputUsername"]'),
            ('password', '//div[@class="form-group"]//input[@id="inputPassword"]'),
            ('submit_button', '//button[normalize-space(.)="Log In"]')])


@Server.address.external_implementation_for(ViaSSUI)
def address(self):
    print "USING SSUI ADDRESS"
    return 'https://{}/self_service/'.format(self.appliance.address)


@Server.login.external_implementation_for(ViaSSUI)
def login(self, user=None, **kwargs):
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = User(credential=cred)
    login_view = navigate_to(self.appliance.server, 'LoginScreen')
    login_view.fill({
        'username': user.credential.principal,
        'password': user.credential.secret,
    })
    login_view.login.click()

    try:
        fill(ssui_form, {'username': user.credential.principal, 'password': user.credential.secret})
    except InvalidElementStateException as e:
        logger.warning("Got an error. Details follow.")
        msg = str(e).lower()
        if "element is read-only" in msg:
            logger.warning("Got a read-only login form, will reload the browser.")
            # Reload browser
            quit()
            ensure_browser_open(url_key=self.appliance.server.address)

    fill(ssui_form, {'username': user.credential.principal, 'password': user.credential.secret})
    sel.click(ssui_form.submit_button)


@navigator.register(Server)
class LoggedIn(SSUINavigateStep):

    def step(self):
        from utils.browser import browser
        browser()
        with self.obj.appliance.context.use(ViaSSUI):
            self.obj.login()


@navigator.register(Server)
class LoginScreen(SSUINavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from utils.browser import ensure_browser_open
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self):
        # Can be either blank or logged in
        del self.view  # In order to unbind the browser
        quit()
        ensure_browser_open(self.obj.appliance.server.address())
        if not self.view.is_displayed:
            raise Exception('Could not open the login screen')
