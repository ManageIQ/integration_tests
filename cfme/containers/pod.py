# -*- coding: utf-8 -*-
from functools import partial
import random
import itertools

from cached_property import cached_property

from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, match_location,\
    PagedTable, CheckboxTable
from cfme.containers.provider import (details_page,
                                      Labelable,
                                      ContainerObjectAllBaseView,
                                      ProviderDetailsView,
                                      UtilizationView)
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep,\
    navigate_to
from navmazing import NavigateToAttribute, NavigateToSibling
from wrapanapi.containers.pod import Pod as ApiPod


list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_group', title='Pods')


class Pod(Taggable, Labelable, SummaryMixin, Navigatable):

    PLURAL = 'Pods'

    def __init__(self, name, project_name, provider, appliance=None):
        self.name = name
        self.provider = provider
        self.project_name = project_name
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiPod(self.provider.mgmt, self.name, self.project_name)

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

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        pod_list = provider.mgmt.list_container_group()
        random.shuffle(pod_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(pod_list, count)]


class PodAllView(ContainerObjectAllBaseView):
    TITLE_TEXT = 'Pods'


@navigator.register(Pod, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = PodAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Pods')

    def resetter(self):
        from cfme.web_ui import paginator
        # Reset view and selection
        tb.select("List View")
        paginator.check_all()
        paginator.uncheck_all()


@navigator.register(Pod, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')
    VIEW = ProviderDetailsView

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.name,
                                                           'Project Name': self.obj.project_name}))


class PodUtilizationView(UtilizationView):
    PLOTS_TITLES = ('Cores Used', 'Memory (MB)', 'Network I/O (KBps)')


@navigator.register(Pod, 'Utilization')
class Utilization(CFMENavigateStep):
    VIEW = PodUtilizationView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.monitor.item_select('Utilization')
