from . import Server
from utils.appliance import ViaSSUI
from utils.appliance.implementations.ssui import navigator, SSUINavigateStep

from cfme import Credential
from cfme.configure.access_control import User
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, fill
from utils import conf
from utils.browser import ensure_browser_open, quit
from utils.log import logger

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
    try:
        fill(ssui_form, {'username': user.credential.principal, 'password': user.credential.secret})
    except sel.InvalidElementStateException as e:
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
