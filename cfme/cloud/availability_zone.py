""" A page functions for Availability Zone
"""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme import BaseLoggedInPage
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import PagedTable, CheckboxTable, toolbar as tb, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator
from widgetastic_manageiq import TimelinesView

# Page specific locators
listview_pagetable = PagedTable(table_locator="//div[@id='list_grid']//table")
listview_checktable = CheckboxTable(table_locator="//div[@id='list_grid']//table")

pol_btn = partial(tb.select, 'Policy')
mon_btn = partial(tb.select, 'Monitoring')

match_page = partial(match_location, controller='availability_zone', title='Availability Zones')


class CloudAvailabilityZoneTimelinesView(TimelinesView, BaseLoggedInPage):
    @property
    def is_displayed(self):
        return self.logged_in_as_current_user and \
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Availability Zones'] and \
            super(TimelinesView, self).is_displayed


class AvailabilityZone(Navigatable):
    def __init__(self, name, provider, appliance):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)


@navigator.register(AvailabilityZone, 'All')
class AvailabilityZoneAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        match_page(summary='Availability Zones')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Availability Zones')


@navigator.register(AvailabilityZone, 'Details')
class AvailabilityZoneDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        tb.select('List View')
        sel.click(listview_pagetable.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name,
             'Cloud Provider': self.obj.provider.name}))


@navigator.register(AvailabilityZone, 'EditTags')
class AvailabilityZoneEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')


@navigator.register(AvailabilityZone, 'Timelines')
class AvailabilityZoneTimelines(CFMENavigateStep):
    VIEW = CloudAvailabilityZoneTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        mon_btn('Timelines')
