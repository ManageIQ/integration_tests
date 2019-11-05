""" A page functions for Availability Zone
"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.common import TimelinesView
from cfme.common.candu_views import AzoneCloudUtilizationView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Table
from widgetastic_manageiq import Text


class AvailabilityZoneToolBar(View):
    """View containing the toolbar widgets"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # Title attribute, no displayed text

    view_selector = View.nested(ItemsToolBarViewSelector)


class AvailabilityZoneDetailsToolBar(View):
    """View containing the toolbar widgets"""
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button(title='Print or export summary')  # Title attribute, no displayed text

    view_selector = View.nested(ItemsToolBarViewSelector)


class AvailabilityZoneEntities(BaseEntitiesView):
    """View containing the widgets for the main content pane"""
    table = Table("//div[@id='gtl_div']//table")
    # todo: remove table and use entities instead


class AvailabilityZoneDetailsEntities(View):
    """View containing the widgets for the main content pane on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')


class AvailabilityZoneDetailsAccordion(View):
    """View containing the accordion widgets for the left side pane on details view"""
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class AvailabilityZoneView(BaseLoggedInPage):
    """Bare bones base view for page header matching"""
    @property
    def in_availability_zones(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Availability Zones']
        )


class AvailabilityZoneAllView(AvailabilityZoneView):
    """Collect the view components into a single view"""
    @property
    def is_displayed(self):
        return(
            self.in_availability_zones and
            self.entities.title.text == 'Availability Zones')

    search = View.nested(Search)
    toolbar = View.nested(AvailabilityZoneToolBar)
    including_entities = View.include(AvailabilityZoneEntities, use_parent=True)

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ProviderAvailabilityZoneAllView(AvailabilityZoneAllView):

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Providers'] and
            self.entities.title.text == '{} (All Availability Zones)'.format(
                self.context['object'].name)
        )


class AvailabilityZoneDetailsView(AvailabilityZoneView):
    """Collect the view components into a single view"""
    @property
    def is_displayed(self):
        obj = self.context['object']
        return (
            self.in_availability_zones and
            self.entities.title.text == obj.expected_details_title and
            self.entities.relationships.get_text_of('Cloud Provider') == obj.provider.name
        )

    toolbar = View.nested(AvailabilityZoneDetailsToolBar)
    sidebar = View.nested(AvailabilityZoneDetailsAccordion)
    entities = View.nested(AvailabilityZoneDetailsEntities)


class CloudAvailabilityZoneTimelinesView(TimelinesView, AvailabilityZoneView):
    pass


@attr.s
class AvailabilityZone(BaseEntity, Taggable, CustomButtonEventsMixin):
    _param_name = "AvailabilityZone"

    name = attr.ib()
    provider = attr.ib()

    def wait_candu_data_available(self, timeout=1200):
        """Waits until C&U data are available for this Availability Zone

        Args:
            timeout: Timeout passed to :py:func:`utils.wait.wait_for`
        """
        view = navigate_to(self, 'Details')
        wait_for(
            lambda: view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=view.browser.refresh
        )


@attr.s
class AvailabilityZoneCollection(BaseCollection):
    ENTITY = AvailabilityZone

    def all(self):
        """returning all Availability Zone objects and support filtering as per provider"""
        provider = self.filters.get("provider")
        azones = self.appliance.rest_api.collections.availability_zones.all
        if provider:
            azone_objs = [
                self.instantiate(name=azone.name, provider=provider)
                for azone in azones
                if provider.id == azone.ems_id
            ]
        else:
            providers = self.appliance.rest_api.collections.providers
            providers_db = {
                prov.id: get_crud_by_name(prov.name)
                for prov in providers
                if "Manager" not in prov.name
            }
            azone_objs = [
                self.instantiate(name=azone.name, provider=providers_db[azone.ems_id])
                for azone in azones
            ]
        return azone_objs


@navigator.register(AvailabilityZoneCollection, 'All')
class AvailabilityZoneAll(CFMENavigateStep):
    VIEW = AvailabilityZoneAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Availability Zones')


@navigator.register(AvailabilityZone, 'Details')
class AvailabilityZoneDetails(CFMENavigateStep):
    VIEW = AvailabilityZoneDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True)
        except ItemNotFound:
            raise ItemNotFound('Could not locate Availability Zone "{}" on provider {}'
                               .format(self.obj.name, self.obj.provider.name))
        row.click()


@navigator.register(AvailabilityZone, 'Timelines')
class AvailabilityZoneTimelines(CFMENavigateStep):
    VIEW = CloudAvailabilityZoneTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(AvailabilityZone, "Utilization")
class Utilization(CFMENavigateStep):
    @property
    def VIEW(self):     # noqa
        # Get provider.azone_utilization_view if one is defined, otherwise default to the
        # AzoneCloudUtilizationView view
        return getattr(self.obj.provider, "azone_utilization_view", AzoneCloudUtilizationView)
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
