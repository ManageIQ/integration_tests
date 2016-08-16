# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb
from cfme.web_ui.menu import nav

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

nav.add_branch(
    'containers_image_registries',
    {
        'containers_image_registry':
        lambda ctx: list_tbl.select_row_by_cells(
            {'Host': ctx['image_registry'].host, 'Provider': ctx['image_registry'].provider.name}),

        'containers_image_registry_detail':
        lambda ctx: list_tbl.click_row_by_cells(
            {'Host': ctx['image_registry'].host, 'Provider': ctx['image_registry'].provider.name}),
    }
)


class ImageRegistry(Taggable, SummaryMixin):

    def __init__(self, host, provider):
        self.host = host
        self.provider = provider

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            self.navigate(detail=True)
        elif refresh:
            tb.refresh()

    def navigate(self, detail=True):
        if detail is True:
            if not self._on_detail_page():
                sel.force_navigate('containers_image_registry_detail',
                    context={'image_registry': self})
        else:
            sel.force_navigate('containers_image_registry',
                context={'image_registry': self})
