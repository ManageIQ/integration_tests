# -*- coding: utf-8 -*-
# added new list_tbl definition
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable
from cfme.web_ui.menu import nav
from . import details_page

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

nav.add_branch(
    'containers_services',
    {
        'containers_service':
<<<<<<< HEAD
        lambda ctx: list_tbl.select_row_by_cells(
            {'Name': ctx['service'].name, 'Provider': ctx['service'].provider.name}),

        'containers_service_detail':
        lambda ctx: list_tbl.click_row_by_cells(
            {'Name': ctx['service'].name, 'Provider': ctx['service'].provider.name}),
=======
        [
            lambda ctx: list_tbl.select_row_by_cells(
                {'Name': ctx['service'].name, 'Provider': ctx['provider'].name}),
            {
                'containers_service_edit_tags':
                lambda _: pol_btn('Edit Tags'),
            }
        ],
        'containers_service_detail':
        [
            lambda ctx: list_tbl.click_row_by_cells(
                {'Name': ctx['service'].name, 'Provider': ctx['provider'].name}),
            {
                'containers_service_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
            }
        ]
>>>>>>> 2f8d888da9f7ed026fd48ca930671aeced168a05
    }
)


class Service(Taggable, SummaryMixin):

    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

    def _on_detail_page(self):
        return sel.is_displayed(
            '//div//h1[contains(., "{} (Summary)")]'.format(self.name))

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
                sel.force_navigate('containers_service_detail', context={'service': self})
        else:
            sel.force_navigate('containers_service', context={'service': self})
