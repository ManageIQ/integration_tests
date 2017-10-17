""" A page functions for Availability Zone
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Dropdown, Button

from cfme.base.login import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import AvailabilityZoneNotFound
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator
from widgetastic_manageiq import (
    TimelinesView, ItemsToolBarViewSelector, Text, Table, Search, PaginationPane, BreadCrumb,
    SummaryTable, Accordion, ManageIQTree)


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


class AvailabilityZoneEntities(View):
    """View containing the widgets for the main content pane"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='gtl_div']//table")
    search = View.nested(Search)


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

    toolbar = View.nested(AvailabilityZoneToolBar)
    entities = View.nested(AvailabilityZoneEntities)
    paginator = PaginationPane()


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
            super(TimelinesView, self).is_displayed)


class AvailabilityZone(WidgetasticTaggable, Navigatable):
    _param_name = "AvailabilityZone"

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)


@navigator.register(AvailabilityZone, 'All')
class AvailabilityZoneAll(CFMENavigateStep):
    VIEW = AvailabilityZoneAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Availability Zones')


@navigator.register(AvailabilityZone, 'Details')
class AvailabilityZoneDetails(CFMENavigateStep):
    VIEW = AvailabilityZoneDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name,
                cloud_provider=self.obj.provider.name)
        except NoSuchElementException:
            raise AvailabilityZoneNotFound('Could not locate Availability Zone "{}" on provider {}'
                                           .format(self.obj.name, self.obj.provider.name))
        row.click()


@navigator.register(AvailabilityZone, 'Timelines')
class AvailabilityZoneTimelines(CFMENavigateStep):
    VIEW = CloudAvailabilityZoneTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')
