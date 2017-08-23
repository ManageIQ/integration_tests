from . import Server
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance.implementations.ssui import navigator, SSUINavigateStep, navigate_to

from cfme.base.credential import Credential
from cfme.configure.access_control import User
from widgetastic_patternfly import Input, Button, FlashMessages
from cfme.utils import conf
from cfme.utils.browser import ensure_browser_open, quit
from cfme.utils.log import logger

from widgetastic.widget import View


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
    login_view = navigate_to(self.appliance.server, 'LoginScreen')
    login_view.fill({
        'username': user.credential.principal,
        'password': user.credential.secret,
    })
    login_view.login.click()
    login_view.flash.assert_no_error()


@navigator.register(Server)
class LoggedIn(SSUINavigateStep):

    def step(self):
        from cfme.utils.browser import browser
        browser()
        with self.obj.appliance.context.use(ViaSSUI):
            self.obj.login()


@navigator.register(Server)
class LoginScreen(SSUINavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from cfme.utils.browser import ensure_browser_open
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self):
        # Can be either blank or logged in
        del self.view  # In order to unbind the browser
        quit()
        ensure_browser_open(self.obj.appliance.server.address())
        if not self.view.is_displayed:
            raise Exception('Could not open the login screen')
