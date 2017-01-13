# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import DestinationNotFound
from cfme.web_ui import match_location, InfoBlock, PagedTable, toolbar as tb
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.version import current_version

match_volumes = partial(match_location, controller='cloud_volume', title='Cloud Volumes')
match_provider = partial(match_location, controller='ems_cloud', title='Cloud Providers')

list_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


def check_version():
    if current_version() >= '5.7':
        raise DestinationNotFound('Cloud Volumes does not exist in CFME 5.7+')


class Volume(Navigatable):

    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.provider = provider


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    def prerequisite(self):
        check_version()
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_volumes(summary='Cloud Volumes')

    def step(self, *args, **kwargs):
        self.parent_view.navigation.select('Compute', 'Clouds', 'Volumes')


@navigator.register(Volume, 'AllByProvider')
class AllByProvider(CFMENavigateStep):
    def prerequisite(self):
        check_version()
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_provider(summary='{} (All Cloud Volumes)'.format(self.obj.provider.name))

    def step(self):
        navigate_to(self.obj.provider, 'Details')
        sel.click(InfoBlock('Relationships', 'Cloud volumes').element)


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_volumes(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        tb.select('List View')
        sel.click(list_tbl.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name, 'Cloud Provider': self.obj.provider.name}))
