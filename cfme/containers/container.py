# -*- coding: utf-8 -*-
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb, paginator, match_location, accordion
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.containers.provider import details_page, pol_btn, mon_btn

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container', title='Containers')


class Container(Taggable, SummaryMixin, Navigatable):

    def __init__(self, name, pod, appliance=None):
        self.name = name
        self.pod = pod
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


@navigator.register(Container, 'All')
class ContainerAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='All Containers')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Containers')

    def resetter(self):
        accordion.tree('Containers', version.pick({
            version.LOWEST: 'All Containers',
            '5.7': 'All Containers (by Pods)',
        }))
        tb.select('List View')
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(Container, 'Details')
class ContainerDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb.select('List View')
        list_tbl.click_row_by_cells({'Name': self.obj.name, 'Pod Name': self.obj.pod})


@navigator.register(Container, 'EditTags')
class ContainerEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(Container, 'Timelines')
class ContainerTimeLines(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@navigator.register(Container, 'Utilization')
class ContainerUtilization(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Utilization')
