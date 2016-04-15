from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav
from cfme.middleware.provider import HawkularProvider
from . import list_tbl

nav.add_branch(
    'middleware_servers',
    {
        'middleware_servers_detail':
            lambda ctx: list_tbl.click_cell('Provider', ctx['provider'].name)
    }
)


class Servers(HawkularProvider):

    def __init__(self, name):
        self.name = name
        self.provider = self.string_name
        self.detail_page_suffix = 'servers_detail'

    def nav_to_servers_view(self):
        sel.force_navigate('middleware_servers', context={'servers': self, 'provider': self.provider})

    def nav_to_detailed_view(self):
        self.load_details()