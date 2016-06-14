from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui.menu import nav
from . import list_tbl, pol_btn, details_page

nav.add_branch(
    'containers_containers',
    {
        'containers_container':
        [
            lambda ctx: list_tbl.select_row_by_cells(
                {'Name': ctx['container'].name, 'Pod Name': ctx['pod'].name}),
            {
                'containers_container_edit_tags':
                lambda _: pol_btn('Edit Tags'),
            }
        ],
        'containers_container_detail':
        [
            lambda ctx: list_tbl.click_row_by_cells(
                {'Name': ctx['container'].name, 'Pod Name': ctx['pod'].name}),
            {
                'containers_container_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
            }
        ]
    }
)


class Container(Taggable):

    def __init__(self, name, pod):
        self.name = name
        self.pod = pod

    def _on_detail_page(self):
        return sel.is_displayed(
            '//div//h1[contains(., "{} (Summary)")]'.format(self.name))

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            self.navigate(detail=True)
        elif refresh:
            tb.refresh()

    def navigate(self, detail=True):
        if detail is True:
            if not self._on_detail_page():
                sel.force_navigate(
                    'containers_container_detail', context={
                        'container': self, 'pod': self.pod})
        else:
            sel.force_navigate('containers_container',
                               context={'container': self, 'pod': self.pod})

    def click_element(self, *ident):
        self.load_details(refresh=True)
        return sel.click(details_page.infoblock.element(*ident))
