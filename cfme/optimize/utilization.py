import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text

from cfme.base.ui import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ManageIQTree

# TODO: FA owner need to develop further model page - add a DetailsView for the BaseEntity.


class UtilizationView(BaseLoggedInPage):
    """Base class for header and nav check"""

    title = Text(locator='//*[@id="explorer_title"]')
    tree = ManageIQTree("treeview-utilization_tree")

    @property
    def in_utilization(self):
        return self.logged_in_as_current_user and self.navigation.currently_selected == [
            "Optimize" if self.context["object"].appliance.version < "5.11" else "Overview",
            "Utilization",
        ]

    @property
    def is_displayed(self):
        region = self.context["object"].appliance.region()
        currently_selected_tree = (
            ["Enterprise", region]
            if self.context["object"].appliance.version > "5.11"
            else [region]
        )
        return (
            self.in_utilization
            and self.tree.currently_selected == currently_selected_tree
            and self.title.text == f'Region "{region}" Utilization Trend Summary'
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
        self.prerequisite_view.navigation.select(
            "Optimize" if self.appliance.version < "5.11" else "Overview", "Utilization"
        )
        if self.appliance.version > "5.11":
            self.view.tree.click_path("Enterprise", self.appliance.region())
