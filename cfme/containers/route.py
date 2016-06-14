from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui.menu import nav
from . import list_tbl, pol_btn, details_page

nav.add_branch(
    'containers_routes',
    {
        'containers_route':
        [
            lambda ctx: list_tbl.select_row_by_cells(
                {'Name': ctx['route'].name, 'Provider': ctx['provider'].name}),
            {
                'containers_route_edit_tags':
                lambda _: pol_btn('Edit Tags'),
            }
        ],
        'containers_route_detail':
        [
            lambda ctx: list_tbl.click_row_by_cells(
                {'Name': ctx['route'].name, 'Provider': ctx['provider'].name}),
            {
                'containers_route_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
            }
        ]
    }
)


class Route(Taggable):

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
                sel.force_navigate(
                    'containers_route_detail', context={
                        'route': self, 'provider': self.provider})
        else:
            sel.force_navigate(
                'containers_route', context={
                    'route': self, 'provider': self.provider})
