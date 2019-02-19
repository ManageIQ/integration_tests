import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text

from cfme.base.ui import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator

# To-Do: FA owner need to develop further model page.


class UtilizationView(BaseLoggedInPage):
    """Base class for header and nav check"""

    title = Text(locator='//*[@id="explorer_title"]')

    @property
    def in_utilization(self):
        return self.logged_in_as_current_user and self.navigation.currently_selected == [
            "Optimize",
            "Utilization",
        ]

    @property
    def is_displayed(self):
        # region = CFME Region: Region 0 [0]'
        region = self.extra.appliance.region()
        return (
            self.in_utilization and
            self.title.text == 'Region "{}" Utilization Trend Summary'.format(region)
        )


@attr.s
class Utilization(BaseEntity):
    region = attr.ib(default=None)
    provider = attr.ib(default=None)
    datastore = attr.ib(default=None)


@attr.s
class UtilizationCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.optimize.utilization.Utilization'."""

    ENTITY = Utilization


@navigator.register(UtilizationCollection, "All")
class All(CFMENavigateStep):
    VIEW = UtilizationView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Optimize", "Utilization")
