# -*- coding: utf-8 -*-
"""A model of an Infrastructure PhysicalChassis in CFME."""
import attr
from lxml.html import document_fromstring
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import Dropdown
from wrapanapi.entities import PhysicalContainer

from cfme.common import BaseLoggedInPage
from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.exceptions import HostStatsNotContains
from cfme.exceptions import ProviderHasNoProperty
from cfme.exceptions import StatsDoNotMatch
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.varmeth import variable
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BreadCrumb
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ParametrizedSummaryTable


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
        return view.entities.summary("Properties").get_text_of("Chassis name")

    @variable(alias='ui')
    def description(self):
        view = navigate_to(self, "Details")
        return view.entities.summary("Properties").get_text_of("Description")

    @variable(alias='ui')
    def identify_led_state(self):
        view = navigate_to(self, "Details")
        return view.entities.summary("Properties").get_text_of("Identify LED State")

    @variable(alias='ui')
    def num_physical_servers(self):
        view = navigate_to(self, "Details")
        return view.entities.summary("Relationships").get_text_of("Physical Servers")

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the physical chassis' information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. An exception will be raised
        if the stats retrieved from the UI do not match those retrieved from wrapanapi.
        """

        # Make sure we are on the physical chassis detail page
        if ui:
            self.load_details()

        # Retrieve the client and the stats and inventory to match
        client = self.provider.mgmt
        stats_to_match = self.STATS_TO_MATCH
        inventory_to_match = self.INVENTORY_TO_MATCH

        # Retrieve the stats and inventory from wrapanapi
        chassis_stats = client.chassis_stats(self, stats_to_match)
        chassis_inventory = client.chassis_inventory(self, inventory_to_match)

        # Refresh the browser
        if ui:
            self.browser.selenium.refresh()

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            logger.debug("Validating stat {} of {}".format(stat, self.name))
            try:
                cfme_stat = int(getattr(self, stat)(method='ui' if ui else None))
                chassis_stat = int(chassis_stats[stat])

                if chassis_stat != cfme_stat:
                    msg = ("The {} stat does not match. "
                        "(chassis: {}, chassis stat: {}, cfme stat: {})")
                    raise StatsDoNotMatch(msg.format(stat, self.name, chassis_stat, cfme_stat))
            except KeyError:
                raise HostStatsNotContains(
                    "Chassis stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))

        # Verify that the inventory retrieved from wrapanapi match those retrieved
        # from the UI
        for inventory in inventory_to_match:
            logger.debug("Validating inventory {} of {}".format(inventory, self.name))
            try:
                cfme_inventory = getattr(self, inventory)(method='ui' if ui else None)
                chass_inventory = chassis_inventory[inventory]

                if chass_inventory != cfme_inventory:
                    msg = "The {} inventory does not match. (server: {}, server inventory: {}, " \
                          "cfme inventory: {})"
                    raise StatsDoNotMatch(msg.format(inventory, self.name, chass_inventory,
                                                     cfme_inventory))
            except KeyError:
                raise HostStatsNotContains(
                    "Server inventory information does not contain '{}'".format(inventory))
            except AttributeError:
                msg = "Provider does not know how to get '{}'"
                raise ProviderHasNoProperty(msg.format(inventory))


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
    def is_displayed(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Chassis"])


class PhysicalChassisEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalChassisEntity, self).data
        if data_dict.get("quadicon", ""):
            quad_data = document_fromstring(data_dict["quadicon"])
            data_dict["no_host"] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
        return data_dict


class PhysicalChassisDetailsToolbar(View):
    """Represents physical chassis toolbar and its controls."""
    identify = Dropdown(text="Identify")


class PhysicalChassisDetailsEntities(View):
    """Represents Details page Entities."""
    summary = ParametrizedSummaryTable


class PhysicalChassisDetailsView(ComputePhysicalInfrastructureChassisView):
    """Main PhysicalChassis details page."""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(PhysicalChassisDetailsToolbar)
    entities = View.nested(PhysicalChassisDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (super(self.__class__, self).is_displayed and
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
        return (super(self.__class__, self).is_displayed and
                self.title.text == "Physical Chassis")


@navigator.register(PhysicalChassisCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PhysicalChassisView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Chassis")


@navigator.register(PhysicalChassis, 'Details')
class Details(CFMENavigateStep):
    VIEW = PhysicalChassisDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
