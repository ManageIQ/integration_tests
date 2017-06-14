# -*- coding: utf-8 -*-
from functools import partial
import random

from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common import SummaryMixin, Taggable
from cfme.containers.provider import pol_btn, navigate_and_get_rows
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb, paginator, match_location,\
    PagedTable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_image_registry',
                     title='Image Registries')


class ImageRegistry(Taggable, SummaryMixin, Navigatable):

    def __init__(self, host, provider, appliance=None):
        self.host = host
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    @property
    def name(self):
        return self.host

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        ir_rows_list = navigate_and_get_rows(provider, cls, count, silent_failure=True)
        random.shuffle(ir_rows_list)
        return [cls(row.host.text, provider, appliance=appliance)
                for row in ir_rows_list]


@navigator.register(ImageRegistry, 'All')
class ImageRegistryAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self):
        return match_page(summary='Image Registries')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Image Registries')

    def resetter(self):
        tb.select('List View')
        if paginator.page_controls_exist():
            sel.check(paginator.check_all())
            sel.uncheck(paginator.check_all())


@navigator.register(ImageRegistry, 'Details')
class ImageRegistryDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.host))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages(
            {'Host': self.obj.host}))


@navigator.register(ImageRegistry, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')
