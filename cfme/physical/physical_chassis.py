# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalChassis in CFME."""
import attr

from lxml.html import document_fromstring
from navmazing import NavigateToSibling, NavigateToAttribute
from cached_property import cached_property
from widgetastic_patternfly import Dropdown, Accordion
from widgetastic.widget import Text, View
from wrapanapi.entities import PhysicalContainer

from cfme.base.login import BaseLoggedInPage
from cfme.common import PolicyProfileAssignable, Taggable
from cfme.common.physical_server_views import (
    PhysicalServerDetailsView,
    PhysicalServerManagePoliciesView,
    PhysicalServersView,
    PhysicalServerProvisionView,
    PhysicalServerTimelinesView,
    PhysicalServerEditTagsView,
    PhysicalServerNetworkDevicesView,
    PhysicalServerStorageDevicesView
)
from cfme.exceptions import (
    ItemNotFound,
    StatsDoNotMatch,
    HostStatsNotContains,
    ProviderHasNoProperty
)
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigate_to, navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import (
    BaseEntitiesView,
    JSBaseEntity,
    BreadCrumb,
    ItemsToolBarViewSelector,
    SummaryTable,
    ManageIQTree
)


@attr.s
class PhysicalChassis(BaseEntity, Updateable, Pretty, PolicyProfileAssignable, Taggable):
    """Model of an Physical Chassis in cfme.

    Args:
        name: Name of the physical chassis.
        custom_ident: The custom identifiter.

    """
    pretty_attrs = ['name', 'custom_ident']

    name = attr.ib()
    provider = attr.ib(default=None)
    ems_ref = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    db_id = None
    mgmt_class = PhysicalContainer

    INVENTORY_TO_MATCH = []
    STATS_TO_MATCH = []

    def load_details(self, refresh=False):
        """To be compatible with the Taggable and PolicyProfileAssignable mixins.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def _execute_button(self, button, option, handle_alert=False):
        view = navigate_to(self, "Details")
        view.toolbar.custom_button(button).item_select(option, handle_alert=handle_alert)
        return view

    @variable(alias='ui')
    def chassis_name(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Chassis name")

    @variable(alias='ui')
    def description(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Description")

    @variable(alias='ui')
    def identify_led_state(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Identify LED State")

    @variable(alias='ui')
    def num_physical_servers(self):
        view = navigate_to(self, "Details")
        return view.entities.relationships.get_text_of("Physical Servers")


@attr.s
class PhysicalChassisCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.physical.physical_chassis.PhysicalChassis`."""

    ENTITY = PhysicalChassis

    def all(self, provider):
        """
        Return all `physical_chassis` objects of the given provider.

        Args:
            provider: the provider that the physical chassis belongs to
        """
        physical_chassis_table = self.appliance.db.client['physical_chassis']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_chassis_query = (
            self.appliance.db.client.session
                .query(physical_chassis_table.name, physical_chassis_table.ems_ref, ems_table.name)
                .join(ems_table, physical_chassis_table.ems_id == ems_table.id))

        if self.filters.get('provider'):
            physical_chassis_query = physical_chassis_query.filter(ems_table.name == provider.name)
        physical_chassiss = []
        for name, ems_ref, ems_name in physical_chassis_query.all():
            physical_chassiss.append(self.instantiate(name=name, ems_ref=ems_ref,
                                    provider=provider or get_crud_by_name(ems_name)))
        return physical_chassiss


class ComputePhysicalInfrastructureChassisView(BaseLoggedInPage):
    """Common parts for chassis views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_chassis(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Chassis"])


class PhysicalChassisEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalChassisEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_host'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
        return data_dict


class PhysicalChassisDetailsToolbar(View):
    """Represents physical chassis toolbar and its controls."""
    identify = Dropdown(text="Identify")


class PhysicalChassisDetailsEntities(View):
    """Represents Details page Entities."""
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")
    management_network = SummaryTable(title="Management Network")
    classis_slots = SummaryTable(title="Chassis Slots")


class PhysicalChassisDetailsView(ComputePhysicalInfrastructureChassisView):
    """Main PhysicalChassis details page."""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(PhysicalChassisDetailsToolbar)
    entities = View.nested(PhysicalChassisDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_chassis and
                self.breadcrumb.active_location == title)


class PhysicalChassisToolbar(View):
    """Represents chassis toolbar and its controls."""
    identify = Dropdown(text="Identify")
    view_selector = View.nested(ItemsToolBarViewSelector)


class PhysicalChassisSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalChassisEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""

    @property
    def entity_class(self):
        return PhysicalChassisEntity


class PhysicalChassisView(ComputePhysicalInfrastructureChassisView):
    toolbar = View.nested(PhysicalChassisToolbar)
    sidebar = View.nested(PhysicalChassisSideBar)
    including_entities = View.include(PhysicalChassisEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_chassis and
                self.title.text == "Physical Chassis")


@navigator.register(PhysicalChassisCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PhysicalChassisView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Chassis")


@navigator.register(PhysicalChassis, 'Details')
class Details(CFMENavigateStep):
    VIEW = PhysicalChassisDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
