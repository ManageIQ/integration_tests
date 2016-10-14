from navmazing import NavigateToSibling

from . import Server

from cfme import BaseLoggedInPage
from cfme.dashboard import DashboardView
from cfme.login import LoginPage

from utils.appliance.endpoints.ui import navigator, CFMENavigateStep


@navigator.register(Server)
class LoginScreen(CFMENavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from utils.browser import ensure_browser_open
        ensure_browser_open()

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
            ensure_browser_open()
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
