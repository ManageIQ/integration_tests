# -*- coding: utf-8 -*-
from functools import partial
import random
import itertools

from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.containers.provider import navigate_and_get_rows,\
    ContainerObjectAllBaseView
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, match_location, InfoBlock,\
    PagedTable, CheckboxTable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from utils.appliance import Navigatable
from wrapanapi.containers.volume import Volume as ApiVolume


list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_volume',
                     title='Volumes')


class Volume(Taggable, SummaryMixin, Navigatable):

    PLURAL = 'Volumes'

    def __init__(self, name, provider, appliance=None):
        self.name = name
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiVolume(self.provider.mgmt, self.name)

    # TODO: remove load_details and dynamic usage from cfme.common.Summary when nav is more complete
    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Volumes"
        Returns: A string representing the contents of the summary's value.
        """
        navigate_to(self, 'Details')
        return InfoBlock.text(*ident)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        rows = navigate_and_get_rows(provider, cls, count=count, silent_failure=True)
        rows = filter(lambda r: r.provider == provider.name, rows)
        random.shuffle(rows)
        return [cls(row.name, row.provider, appliance=appliance)
                for row in itertools.islice(rows, count)]


class VolumeAllView(ContainerObjectAllBaseView):
    TITLE_TEXT = 'Persistent Volumes'


@navigator.register(Volume, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = VolumeAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Volumes')

    def resetter(self):
        from cfme.web_ui import paginator
        tb.select('Grid View')
        paginator.check_all()
        paginator.uncheck_all()


@navigator.register(Volume, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Name': self.obj.name}))
