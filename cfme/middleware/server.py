import re
from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import nav, toolbar as tb
from utils.db import cfmedb
from . import LIST_TABLE_LOCATOR, mon_btn, pwr_btn, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, server=None, provider=None):
    t_ms = cfmedb()['middleware_servers']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_ms.name, t_ms.feed,
                                   t_ms.product, t_ems.name).join(t_ems, t_ms.ems_id == t_ems.id)
    if name:
        query = query.filter(t_ms.name == name)
    if server:
        query = query.filter(t_ms.nativeid.like('%{}%'.format(server)))
    if provider:
        query = query.filter(t_ems.name == provider)
    return query

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
    def servers(cls, provider=None):
        servers = []
        if provider:
            # if provider instance is provided try to navigate provider's servers page
            # if no servers are registered in provider, returns empty list
            if not provider.load_all_provider_servers():
                return []
        else:
            # if provider instance is not provided then navigates  to all servers page
            sel.force_navigate('middleware_servers')
        if sel.is_displayed(list_tbl):
            for page in paginator.pages():
                for row in list_tbl.rows():
                    servers.append(MiddlewareServer(name=row.server_name.text,
                                                    id=row.feed.text,
                                                    product=row.product.text,
                                                    provider=row.provider.text))
        return servers

    @classmethod
    def headers(cls):
        sel.force_navigate('middleware_servers')
        headers = [sel.text(hdr).encode("utf-8")
                   for hdr in sel.elements("//thead/tr/th") if hdr.text]
        return headers

    @classmethod
    def servers_in_db(cls, server=None, provider=None):
        servers = []
        rows = _db_select_query(server=server, provider=(provider.name if provider else None)).all()
        for server in rows:
            servers.append(MiddlewareServer(name=server[0], id=server[1],
                                            product=server[2], provider=server[3]))
        return servers

    @classmethod
    def servers_in_mgmt(cls, provider):
        servers = []
        rows = provider.mgmt.list_server()
        for server in rows:
            servers.append(MiddlewareServer(provider=provider.name,
                    id=server.path.feed, name=re.sub(r'~~$', '', server.path.resource),
                    product=server.data['Product Name']))
        return servers

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
