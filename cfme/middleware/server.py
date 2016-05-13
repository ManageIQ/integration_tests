from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable
from cfme.web_ui.menu import nav, toolbar as tb
from . import LIST_TABLE_LOCATOR, mon_btn, pwr_btn, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)

nav.add_branch(
    'middleware_servers', {
        'middleware_server': lambda ctx: list_tbl.select_row('Server Name', ctx['name']),
        'middleware_server_detail':
            lambda ctx: list_tbl.click_row_by_cells({'Server Name': ctx['name']}),
    }
)


class MiddlewareServer(MiddlewareBase, Taggable):
    """
    MiddlewareServer class provides actions and details on Server page.
    Class method available to get existing servers list

    Args:
        name: name of the server
        provider: Provider object (HawkularProvider)
        product: Product type of the server
        id: Native id(internal id) of the server

    Usage:

        myserver = MiddlewareServer(name='Foo.war', provider=haw_provider)
        myserver.reload_server()

        myservers = MiddlewareServer.servers()

    """
    property_tuples = [('name', 'name')]

    def __init__(self, name, provider=None, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.product = kwargs['product'] if 'product' in kwargs else None
        self.id = kwargs['id'] if 'id' in kwargs else None

    @classmethod
    def servers(cls, provider):
        sel.force_navigate('middleware_servers')
        deployments = []
        for row in list_tbl.rows():
            deployments.append(MiddlewareServer(
                provider=provider, name=row.server_name.text, product=row.product.text))
        return deployments

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            sel.force_navigate('middleware_server_detail', context={'name': self.name})
        if refresh:
            tb.refresh()

    def reload_server(self):
        self.load_details(refresh=True)
        pwr_btn("Reload Server", invokes_alert=True)
        sel.handle_alert()

    def stop_server(self):
        self.load_details(refresh=True)
        pwr_btn("Stop Server", invokes_alert=True)
        sel.handle_alert()

    def open_utilization(self):
        self.load_details(refresh=True)
        mon_btn("Utilization")
