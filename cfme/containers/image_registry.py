from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from cfme.web_ui.menu import nav

from . import list_tbl, pol_btn

nav.add_branch(
    'containers_image_registries',
    {
        'containers_image_registry':
        [
            lambda ctx: list_tbl.select_row_by_cells(
                {'Host': ctx['image_registry'].host, 'Provider': ctx['provider'].name}),
            {
                'containers_image_registry_edit_tags':
                lambda _: pol_btn('Edit Tags'),
            }
        ],
        'containers_image_registry_detail':
        [
            lambda ctx: list_tbl.click_row_by_cells(
                {'Host': ctx['image_registry'].host, 'Provider': ctx['provider'].name}),
            {
                'containers_image_registry_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
            }
        ]
    }
)


class ImageRegistry(Taggable):

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
                    context={'image_registry': self, 'provider': self.provider})
        else:
            sel.force_navigate('containers_image_registry',
                context={'image_registry': self, 'provider': self.provider})
