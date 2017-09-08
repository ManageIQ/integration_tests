# -*- coding: utf-8 -*-
from functools import partial
import random
import itertools

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_manageiq import Accordion, ManageIQTree, View, Table
from widgetastic_patternfly import VerticalNavigation
from widgetastic.widget import Text
from widgetastic.xpath import quote
from widgetastic.utils import Version, VersionPick

from cfme.containers.provider import details_page, pol_btn, mon_btn,\
    ContainerObjectAllBaseView
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb, match_location, PagedTable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils import version


list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container', title='Containers')


class Container(Taggable, SummaryMixin, Navigatable):

    PLURAL = 'Containers'

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

    @property
    def project_name(self):
        return self.pod.project_name

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        containers_list = provider.mgmt.list_container()
        random.shuffle(containers_list)
        return [cls(obj.name, obj.cg_name, appliance=appliance)
                for obj in itertools.islice(containers_list, count)]


class ContainerAllView(ContainerObjectAllBaseView):
    """Containers All view"""
    TITLE_TEXT = VersionPick({
        Version.lowest(): '//h3[normalize-space(.) = {}]'.format(quote('All Containers')),
        '5.8': '//h1[normalize-space(.) = {}]'.format(quote('Containers'))
    })
    summary = Text(TITLE_TEXT)
    containers = Table(locator="//div[@id='list_grid']//table")

    @property
    def table(self):
        return self.containers

    def title(self):
        return self.summary

    @View.nested
    class Filters(Accordion):  # noqa
        ACCORDION_NAME = "Filters"

        @View.nested
        class Navigation(VerticalNavigation):
            DIV_LINKS_MATCHING = './/div/ul/li/a[contains(text(), {txt})]'

            def __init__(self, parent, logger=None):
                VerticalNavigation.__init__(self, parent, '#Container_def_searches', logger=logger)

        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return self.summary.is_displayed


@navigator.register(Container, 'All')
class ContainerAll(CFMENavigateStep):
    VIEW = ContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Containers')

    def resetter(self):
        if version.current_version() < '5.8':
            self.view.Filters.tree.click_path('All Containers')
        else:
            self.view.Filters.Navigation.select('ALL (Default)')
        tb.select('List View')
        from cfme.web_ui import paginator
        if paginator.page_controls_exist():
            paginator.check_all()
            paginator.uncheck_all()


@navigator.register(Container, 'Details')
class ContainerDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages(
            {'Name': self.obj.name, 'Pod Name': self.obj.pod}))


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
