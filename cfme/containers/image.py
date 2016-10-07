# -*- coding: utf-8 -*-
# added new list_tbl definition
from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable, paginator, summary_title, InfoBlock
from utils.appliance.endpoints.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import Navigatable

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


def match_title_and_controller():
    title_match = sel.execute_script('return document.title;') == 'CFME: Images'
    controller_match = sel.execute_script('return ManageIQ.controller;') == 'container_image'
    return title_match and controller_match


class Image(Taggable, SummaryMixin, Navigatable):

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    # TODO: remove load_details and dynamic usage from cfme.common.Summary when nav is more complete
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
        navigate_to(self, 'Details')
        return InfoBlock.text(*ident)


@navigator.register(Image, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Compute', 'Containers', 'Container Images')(None)

    def resetter(self):
        tb.select('Grid View')
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        summary_match = summary_title() == '{} (Summary)'.format(self.obj.name)
        return summary_match and match_title_and_controller()

    def step(self):
        tb.select('List View')
        list_tbl.click_row_by_cells({'Name': self.obj.name})
