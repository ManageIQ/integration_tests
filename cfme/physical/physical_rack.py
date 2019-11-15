"""A model of an Infrastructure PhysicalRack in CFME."""
import attr
from lxml.html import document_fromstring
from navmazing import NavigateToAttribute
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import Taggable
from cfme.exceptions import ProviderHasNoProperty
from cfme.exceptions import RackStatsDoesNotContain
from cfme.exceptions import StatsDoNotMatch
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.update import Updateable
from cfme.utils.varmeth import variable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BreadCrumb
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import SummaryTable


@attr.s
class PhysicalRack(BaseEntity, Updateable, Pretty, Taggable):
    """Model of an Physical Rack in cfme.

    Args:
        name: Name of the physical rack.
        custom_ident: The custom identifiter.
        provider: The physical provider.

    Usage:
        myrack = PhysicalRack()
        myrack.create()

    """
    pretty_attrs = ['name', 'custom_ident']

    name = attr.ib()
    provider = attr.ib()
    ems_ref = attr.ib(default=None)
    custom_ident = attr.ib(default=None)
    db_id = None

    INVENTORY_TO_MATCH = ['power_state']
    STATS_TO_MATCH = ['cores_capacity', 'memory_capacity']

    def refresh(self, cancel=False):
        """Perform 'Refresh Relationships and Power States' for the rack.

        Args:
            cancel (bool): Whether the action should be cancelled, default to False
        """
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Refresh Relationships and Power States",
                                               handle_alert=cancel)

    def load_details(self, refresh=False):
        """To be compatible with the Taggable mixin.

        Args:
            refresh (bool): Whether to perform the page refresh, defaults to False
        """
        view = navigate_to(self, "Details")
        if refresh:
            view.browser.refresh()
            view.flush_widget_cache()

    def wait_for_physical_rack_state_change(self, desired_state, timeout=300):
        """Wait for PhysicalRack to come to desired state. This function waits just the needed amount of
           time thanks to wait_for.

        Args:
            desired_state (str): 'on' or 'off'
            timeout (int): Specify amount of time (in seconds) to wait until TimedOutError is raised
        """
        view = navigate_to(self.parent, "All")

        def _looking_for_state_change():
            entity = view.entities.get_entity(name=self.name)
            return "currentstate-{}".format(desired_state) in entity.data['state']

        wait_for(_looking_for_state_change, fail_func=view.browser.refresh, num_sec=timeout)

    @variable(alias="ui")
    def rack_name(self):
        view = navigate_to(self, "Details")
        return view.entities.properties.get_text_of("Rack name")

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the physical rack's information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. An exception will be raised
        if the stats retrieved from the UI do not match those retrieved from wrapanapi.
        """

        # Retrieve the client and the stats and inventory to match
        client = self.provider.mgmt
        stats_to_match = self.STATS_TO_MATCH
        inventory_to_match = self.INVENTORY_TO_MATCH

        # Retrieve the stats and inventory from wrapanapi
        rack_stats = client.stats(*stats_to_match, requester=self)
        rack_inventory = client.inventory(*inventory_to_match, requester=self)

        # Refresh the browser
        if ui:
            navigate_to(self, 'Details', wait_for_view=True)

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            try:
                cfme_stat = int(getattr(self, stat)(method='ui' if ui else None))
                rack_stat = int(rack_stats[stat])

                if rack_stat != cfme_stat:
                    msg = "The {} stat does not match. (rack: {}, rack stat: {}, cfme stat: {})"
                    raise StatsDoNotMatch(msg.format(stat, self.name, rack_stat, cfme_stat))
            except KeyError:
                raise RackStatsDoesNotContain(
                    "Rack stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))

        # Verify that the inventory retrieved from wrapanapi match those retrieved
        # from the UI
        for inventory in inventory_to_match:
            try:
                cfme_inventory = getattr(self, inventory)(method='ui' if ui else None)
                rack_inventory = rack_inventory[inventory]

                if rack_inventory != cfme_inventory:
                    msg = "The {} inventory does not match. (rack: {}, rack inventory: {}, " \
                          "cfme inventory: {})"
                    raise StatsDoNotMatch(msg.format(inventory, self.name, rack_inventory,
                                                     cfme_inventory))
            except KeyError:
                raise RackStatsDoesNotContain(
                    "Rack inventory information does not contain '{}'".format(inventory))
            except AttributeError:
                msg = "Provider does not know how to get '{}'"
                raise ProviderHasNoProperty(msg.format(inventory))


@attr.s
class PhysicalRackCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.host.PhysicalRack`."""

    ENTITY = PhysicalRack

    def select_entity_rows(self, *physical_racks):
        """ Select all physical rack objects """
        physical_racks = list(physical_racks)
        checked_physical_racks = list()
        view = navigate_to(self, 'All')

        for physical_rack in physical_racks:
            view.entities.get_entity(name=physical_rack.name, surf_pages=True).check()
            checked_physical_racks.append(physical_rack)
        return view

    def all(self, provider=None):
        """returning all physical_racks objects"""
        physical_rack_table = self.appliance.db.client['physical_racks']
        ems_table = self.appliance.db.client['ext_management_systems']
        physical_rack_query = (
            self.appliance.db.client.session
                .query(physical_rack_table.name, physical_rack_table.ems_ref, ems_table.name)
                .join(ems_table, physical_rack_table.ems_id == ems_table.id))

        if provider is None:
            provider = self.filters.get('provider')

        if provider:
            physical_rack_query = physical_rack_query.filter(ems_table.name == provider.name)
        return [
            self.instantiate(name=name, ems_ref=ems_ref, provider=provider
                or get_crud_by_name(ems_name))
            for name, ems_ref, ems_name in physical_rack_query.all()
        ]


class ComputePhysicalInfrastructureRacksView(BaseLoggedInPage):
    """Common parts for rack views."""
    title = Text('.//div[@id="center_div" or @id="main-content"]//h1')

    @property
    def in_compute_physical_infrastructure_racks(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ["Compute", "Physical Infrastructure",
                                                       "Racks"])


class PhysicalRackEntity(JSBaseEntity):
    @property
    def data(self):
        data_dict = super(PhysicalRackEntity, self).data
        if 'quadicon' in data_dict and data_dict['quadicon']:
            quad_data = document_fromstring(data_dict['quadicon'])
            data_dict['no_host'] = int(quad_data.xpath(self.QUADRANT.format(pos="a"))[0].text)
        return data_dict


class PhysicalRackDetailsToolbar(View):
    """Represents physical rack toolbar and its controls."""
    configuration = Dropdown(text="Configuration")


class PhysicalRackDetailsEntities(View):
    """Represents Details page Entities."""
    properties = SummaryTable(title="Properties")
    relationships = SummaryTable(title="Relationships")


class PhysicalRackDetailsView(ComputePhysicalInfrastructureRacksView):
    """Main PhysicalRack details page."""
    breadcrumb = BreadCrumb()
    toolbar = View.nested(PhysicalRackDetailsToolbar)
    entities = View.nested(PhysicalRackDetailsEntities)

    @property
    def is_displayed(self):
        title = "{name} (Summary)".format(name=self.context["object"].name)
        return (self.in_compute_physical_infrastructure_racks and
                self.breadcrumb.active_location == title)


class PhysicalRacksToolbar(View):
    """Represents racks toolbar and its controls."""
    configuration = Dropdown(text="Configuration")
    view_selector = View.nested(ItemsToolBarViewSelector)


class PhysicalRackSideBar(View):
    """Represents left side bar. It usually contains navigation, filters, etc."""

    @View.nested
    class filters(Accordion): # noqa
        tree = ManageIQTree()


class PhysicalRackEntitiesView(BaseEntitiesView):
    """Represents the view with different items like hosts."""
    @property
    def entity_class(self):
        return PhysicalRackEntity


class PhysicalRacksView(ComputePhysicalInfrastructureRacksView):
    toolbar = View.nested(PhysicalRacksToolbar)
    sidebar = View.nested(PhysicalRackSideBar)
    including_entities = View.include(PhysicalRackEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return (self.in_compute_physical_infrastructure_racks and
                self.title.text == "Physical Racks")


@navigator.register(PhysicalRackCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PhysicalRacksView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Compute", "Physical Infrastructure", "Racks")


@navigator.register(PhysicalRack, 'Details')
class Details(CFMENavigateStep):
    VIEW = PhysicalRackDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
