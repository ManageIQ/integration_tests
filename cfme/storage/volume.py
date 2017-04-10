# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import match_location, PagedTable, toolbar as tb
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to

match_volumes = partial(match_location, controller='cloud_volume', title='Cloud Volumes')
match_provider = partial(match_location, controller='ems_cloud', title='Cloud Providers')

list_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


class Volume(Navigatable):
    def __init__(self, name, provider, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.provider = provider


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    def prerequisite(self):
        navigate_to(self.obj.appliance.server, 'LoggedIn')

    def am_i_here(self):
        return match_volumes(summary='Cloud Volumes')

    def step(self):
        if self.obj.appliance.version < '5.7':
            self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Volumes')
        else:
            self.prerequisite_view.navigation.select('Storage', 'Volumes')


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_volumes(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(list_tbl.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name, 'Cloud Provider': self.obj.provider.name}))
