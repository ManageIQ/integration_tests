from navmazing import NavigateToSibling
from widgetastic.widget import Text

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class MigrationView(BaseLoggedInPage):
    title = Text("#explorer_title_text")

    @property
    def in_explorer(self):
        return self.logged_in_as_current_user and (
            self.navigation.currently_selected == ["Compute", "Migration"]
            or self.navigation.currently_selected == ["Compute", "Migration", "Migration Plans"]
        )

    @property
    def is_displayed(self):
        return self.in_explorer


@navigator.register(Server)
class Migration(CFMENavigateStep):
    VIEW = MigrationView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Compute", "Migration")
