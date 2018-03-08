from navmazing import NavigateToSibling
from widgetastic_manageiq import TimelinesView, ManageIQTree
from widgetastic.widget import View
from widgetastic_patternfly import Accordion

from cfme.base import Server
from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep


class IntelTimelinesView(BaseLoggedInPage, TimelinesView):
    @View.nested
    class timelines(Accordion):  # noqa
        tree = ManageIQTree()
        ACCORDION_NAME = "Timelines"

    @property
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Cloud Intel", "Timelines"] and
                self.title.text == 'Timelines'
                )

    @property
    def is_timeline_displayed(self):
        return (bool(self.chart.get_categories()) and
                self.title.text == self.context['object'].title)


@navigator.register(Server)
class IntelTimelines(CFMENavigateStep):
    VIEW = IntelTimelinesView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self):
        self.view.navigation.select("Cloud Intel", 'Timelines')
