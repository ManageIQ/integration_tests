# -*- coding: utf-8 -*-
# added new list_tbl definition
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable, paginator, match_location
from cfme.containers.provider import details_page
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep,\
    navigate_to
from navmazing import NavigateToAttribute, NavigateToSibling
from functools import partial

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container_replicators', title='Replicators')


class Replicator(Taggable, SummaryMixin, Navigatable):

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def click_element(self, *ident):
        self.load_details(refresh=True)
        return sel.click(details_page.infoblock.element(*ident))

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        return details_page.infoblock.text(*ident)


@navigator.register(Replicator, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Replicators')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Replicator, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        list_tbl.click_row_by_cells({'Name': self.obj.name})
