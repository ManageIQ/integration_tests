from navmazing import NavigateToSibling
from widgetastic.widget import Text
from widgetastic_patternfly import Button

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator


class ControlLogView(BaseLoggedInPage):
    """Basic view for Control/Log tab."""
    title = Text(".//div[@id='main-content']//h1")
    subtitle = Text(".//div[@id='main_div']/h3")
    refresh_button = Button(id="refresh_log")
    download = Button(id="fetch_log")

    @property
    def is_displayed(self):
        return (
            self.title.text == "Log" and
            "Last 1000 lines from server" in self.subtitle.text and
            self.refresh_button.is_displayed and
            self.download.is_displayed
        )


@navigator.register(Server)
class ControlLog(CFMENavigateStep):
    VIEW = ControlLogView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self, *args, **kwargs):
        self.view.navigation.select("Control", "Log")
