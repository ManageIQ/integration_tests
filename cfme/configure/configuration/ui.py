from . import Server

from utils.appliance.endpoints.ui import navigator, CFMENavigateStep
from fixtures.pytest_store import store


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    def step(self):
        from cfme.login import login
        from utils.browser import browser
        browser()
        login(store.user)
