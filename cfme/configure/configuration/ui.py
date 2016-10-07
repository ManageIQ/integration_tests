from . import Server

from utils.appliance.endpoints.ui import navigator, CFMENavigateStep


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    def step(self):
        from cfme.login import login
        from utils.browser import browser
        browser()
        login(self.obj.appliance.user)
