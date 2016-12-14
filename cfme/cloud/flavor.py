""" Page functions for Flavor pages


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import PagedTable, toolbar as tb, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator

listview_table = PagedTable(table_locator="//div[@id='list_grid']//table")

pol_btn = partial(tb.select, 'Policy')

match_page = partial(match_location, controller='flavor', title='Flavors')


class Flavor(Navigatable):
    """
    Flavor class to support navigation
    """

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)


@navigator.register(Flavor, 'All')
class FlavorAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Flavors')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Flavors')


@navigator.register(Flavor, 'Details')
class FlavorDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self, *args, **kwargs):
        sel.click(listview_table.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name,
             'Cloud Provider': self.obj.provider.name}))


@navigator.register(Flavor, 'EditTags')
class FlavorEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        pol_btn('Edit Tags')
