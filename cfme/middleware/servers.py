from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui.menu import nav
from . import list_tbl

nav.add_branch(
    'middleware_servers',
    {
        'middleware_servers_detail':
            lambda ctx: list_tbl.click_cell('Provider', ctx['provider'].name)
    }
)


class Servers(object):

    def __init__(self, name):
        self.name = name
        self.provider = 'Middleware'
        self.detail_page_suffix = 'servers_detail'

    def nav_to_servers_view(self):
        sel.force_navigate('middleware_servers', context={
            'servers': self, 'provider': self.provider})

    def nav_to_detailed_view(self):
        sel.force_navigate('middleware_servers_detail', context={
            'provider': self})

    def validate_server_details(self):
        print("Server Detail Validation TBD")
