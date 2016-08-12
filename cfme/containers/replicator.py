# -*- coding: utf-8 -*-
# added new list_tbl definition
from __future__ import unicode_literals
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable
from cfme.web_ui.menu import nav
from . import details_page

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

nav.add_branch(
    'containers_replicators',
    {
        'containers_replicator':
        lambda ctx: list_tbl.select_row_by_cells(
            {'Name': ctx['replicator'].name, 'Provider': ctx['replicator'].provider.name}),

        'containers_replicator_detail':
        lambda ctx: list_tbl.click_row_by_cells(
            {'Name': ctx['replicator'].name, 'Provider': ctx['replicator'].provider.name}),
    }
)


class Replicator(Taggable, SummaryMixin):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _on_detail_page(self):
        return sel.is_displayed('//div//h1[contains(., "{} (Summary)")]'.format(self.name))

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            self.navigate(detail=True)
        elif refresh:
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

    def navigate(self, detail=True):
        if detail is True:
            if not self._on_detail_page():
                sel.force_navigate('containers_replicator_detail', context={'replicator': self})
        else:
            sel.force_navigate('containers_replicator', context={'replicator': self})
