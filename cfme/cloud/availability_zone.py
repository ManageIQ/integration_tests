""" A page functions for Availability Zone
"""
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Dropdown, Button, BreadCrumb

from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable
from cfme.exceptions import AvailabilityZoneNotFound, ItemNotFound
from cfme.modeling.base import BaseEntity, BaseCollection
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from widgetastic_manageiq import (
    BaseEntitiesView, TimelinesView, ItemsToolBarViewSelector, Text, Table, SummaryTable, Accordion,
    ManageIQTree, Search)


class AvailabilityZoneToolBar(View):
    """View containing the toolbar widgets"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')  # Title attribute, no displayed text

    view_selector = View.nested(ItemsToolBarViewSelector)


class AvailabilityZoneDetailsToolBar(View):
    """View containing the toolbar widgets"""
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button(title='Download summary in PDF format')  # Title attribute, no displayed text

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
        expected_title = "{} (Summary)".format(self.context['object'].name)
        expected_detail = self.context['object'].provider.name
        return (
            self.in_availability_zones and
            self.entities.title.text == expected_title and
            self.entities.relationships.get_text_of('Cloud Provider') == expected_detail)

    toolbar = View.nested(AvailabilityZoneDetailsToolBar)
    sidebar = View.nested(AvailabilityZoneDetailsAccordion)
    entities = View.nested(AvailabilityZoneDetailsEntities)


class CloudAvailabilityZoneTimelinesView(TimelinesView, AvailabilityZoneView):
    @property
    def is_displayed(self):
        return (
            self.in_availability_zones and
            self.breadcrumb.active_location == 'Timelines' and
            "{} (Summary)".format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)


@attr.s
class AvailabilityZone(BaseEntity, Taggable):
    _param_name = "AvailabilityZone"

    name = attr.ib()
    provider = attr.ib()


@attr.s
class AvailabilityZoneCollection(BaseCollection):
    ENTITY = AvailabilityZone


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
            raise AvailabilityZoneNotFound('Could not locate Availability Zone "{}" on provider {}'
                                           .format(self.obj.name, self.obj.provider.name))
        row.click()


@navigator.register(AvailabilityZone, 'Timelines')
class AvailabilityZoneTimelines(CFMENavigateStep):
    VIEW = CloudAvailabilityZoneTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')
