# -*- coding: utf-8 -*-
from cfme.common import SummaryMixin, Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb
from cfme.web_ui.menu import nav
from cfme.configure import details_page


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

    def _on_detail_page(self):
        return sel.is_displayed(
            '//div//h1[contains(., "{} (Summary)")]'.format(self.host))

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

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.load_details(refresh=True)
        return details_page.infoblock.text(*ident)

    @staticmethod
    def get_names():
        sel.force_navigate('containers_image_registries')
        return map(lambda r: r.host.text, list_tbl.rows())
