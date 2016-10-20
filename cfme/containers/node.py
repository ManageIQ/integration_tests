# -*- coding: utf-8 -*-
# added new list_tbl definition
from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb, paginator, InfoBlock, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from . import pol_btn, mon_btn

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container_node', title='Nodes')


class Node(Taggable, SummaryMixin, Navigatable):

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the summary's value.
        """
        self.load_details(refresh=False)
        return InfoBlock.text(*ident)


@navigator.register(Node, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Nodes')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Containers', 'Container Nodes')(None)

    def resetter(self):
        # Reset view and selection
        tb.select("List View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Node, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        # Assuming default list view from prerequisite
        list_tbl.click_row_by_cells({'Name': self.obj.name, 'Provider': self.obj.provider.name})


@navigator.register(Node, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        match_page(summary='Tag Assignment')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(Node, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        match_page(summary='Select Policy Profiles')

    def step(self):
        pol_btn('Manage Policies')


@navigator.register(Node, 'Utilization')
class Utilization(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        match_page(summary='{} Capacity & Utilization'.format(self.obj.name))

    def step(self):
        mon_btn('Utilization')
