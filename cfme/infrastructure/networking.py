import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import SummaryTable


@attr.s
class InfraSwitches(BaseEntity, Taggable, CustomButtonEventsMixin):
    """ Model of an infrastructure cluster in cfme

    Args:
        name: Name of the switch.
    """

    name = attr.ib()


@attr.s
class InfraSwitchesCollection(BaseCollection):
    """Collection object for the :py:class:`cmfe.infrastructure.networking.InfraNetworking`."""

    ENTITY = InfraSwitches

    def all(self):
        """List of all switch objects"""
        view = navigate_to(self, "All")
        return [self.instantiate(ent) for ent in view.entities.entity_names]


class InfraNetworkingView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""

    @property
    def in_infra_networking(self):
        nav_chain = ["Compute", "Infrastructure", "Networking"]
        return self.logged_in_as_current_user and self.navigation.currently_selected == nav_chain


class InfraNetworkingToolbar(View):
    """The toolbar for Infra Networking view"""

    policy = Dropdown("Policy")
    view_selector = View.nested(ItemsToolBarViewSelector)


class InfraSwitchesAllView(InfraNetworkingView):
    """Infra switch all view"""

    @property
    def is_displayed(self):
        return self.in_infra_networking and self.entities.title.text == "All Switches"

    toolbar = View.nested(InfraNetworkingToolbar)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @View.nested
    class switches(Accordion):  # noqa
        ACCORDION_NAME = "Switches"
        tree = ManageIQTree()


class InfraSwitchesDetailsEntities(View):
    """The entities on the detail page"""

    title = Text('//*[@id="explorer_title_text"]')
    relationships = SummaryTable("Relationships")
    smart_management = SummaryTable("Smart Management")


class InfraNetworkingDetailsView(InfraNetworkingView):
    """The details page of a switch"""

    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        expected_title = 'Switch "{}"'.format(self.context["object"].name)
        return self.in_infra_networking and self.entities.title.text == expected_title

    toolbar = View.nested(InfraNetworkingToolbar)
    entities = View.nested(InfraSwitchesDetailsEntities)


@navigator.register(InfraSwitchesCollection)
class All(CFMENavigateStep):
    VIEW = InfraSwitchesAllView

    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Infrastructure", "Networking")

    def resetter(self, *args, **kwargs):
        self.view.switches.tree.fill(["All Distributed Switches"])


@navigator.register(InfraSwitches)
class Details(CFMENavigateStep):
    VIEW = InfraNetworkingDetailsView

    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
