from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav
from . import list_tbl


nav.add_branch(
    'middleware_providers',
    {
        'middleware_provider_detail':
            lambda ctx: list_tbl.click_cells({'name': ctx['provider'].name})
    }
)


class Providers(object):

    def __init__(self, name):
        self.name = name
        self.provider = 'Middleware'
        self.detail_page_suffix = 'provider_detail'

    def nav_to_providers_view(self):
        sel.force_navigate('middleware_providers', context={
            'providers': self, 'provider': self.provider})

    def nav_to_provider_detailed_view(self):
        if not self._on_detail_page():
            sel.force_navigate('middleware_provider_detail', context={
                'provider': self})

    def _on_detail_page(self):
        return sel.is_displayed_text("{} (Summary)".format(self.name))
