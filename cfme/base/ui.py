from navmazing import NavigateToSibling

from . import Server

from utils.appliance.endpoints.ui import navigator, CFMENavigateStep


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    def step(self):
        from cfme.login import login
        from utils.browser import browser
        browser()
        login(self.obj.appliance.user)


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
