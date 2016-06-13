import re
from cfme.common import Taggable
from mgmtsystem.hawkular import Path
from cfme.exceptions import MiddlewareServerNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import nav, toolbar as tb
from cfme.middleware import parse_properties
from utils import attributize_string
from utils.db import cfmedb
from utils.providers import get_crud, get_provider_key, list_middleware_providers
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, mon_btn, pwr_btn, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, feed=None, provider=None):
    """column order: `name`, `hostname`, `feed`, `product`,
    `provider_name`, `ems_ref`, `properties`"""
    t_ms = cfmedb()['middleware_servers']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_ms.name, t_ms.hostname, t_ms.feed, t_ms.product,
                                   t_ems.name.label('provider_name'),
                                   t_ms.ems_ref, t_ms.properties)\
        .join(t_ems, t_ms.ems_id == t_ems.id)
    if name:
        query = query.filter(t_ms.name == name)
    if feed:
        query = query.filter(t_ms.feed == feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    return query


def _get_servers_page(provider):
    if provider:  # if provider instance is provided navigate through provider's servers page
        provider.summary.reload()
        if provider.summary.relationships.middleware_servers.value == 0:
            return
        provider.summary.relationships.middleware_servers.click()
    else:  # if None(provider) given navigate through all middleware servers page
        sel.force_navigate('middleware_servers')

nav.add_branch(
    'middleware_servers', {
        'middleware_server': lambda ctx: list_tbl.select_row('Server Name', ctx['name']),
    }
)


class MiddlewareServer(MiddlewareBase, Taggable):
    """
    MiddlewareServer class provides actions and details on Server page.
    Class method available to get existing servers list

    Args:
        name: name of the server
        hostname: Host name of the server
        provider: Provider object (HawkularProvider)
        product: Product type of the server
        feed: feed of the server

    Usage:

        myserver = MiddlewareServer(name='Foo.war', provider=haw_provider)
        myserver.reload_server()

        myservers = MiddlewareServer.servers()

    """
    property_tuples = [('name', 'name'), ('feed', 'feed'),
                       ('hostname', 'hostname'), ('bound_address', 'bind_address'),
                       ('product_name', 'product'), ('version', 'version')]

    def __init__(self, name, provider=None, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.product = kwargs['product'] if 'product' in kwargs else None
        self.hostname = kwargs['hostname'] if 'hostname' in kwargs else None
        self.feed = kwargs['feed'] if 'feed' in kwargs else None
        if 'properties' in kwargs:
            for property in kwargs['properties']:
                setattr(self, attributize_string(property), kwargs['properties'][property])

    @classmethod
    def servers(cls, provider=None, strict=True):
        servers = []
        _get_servers_page(provider=provider)
        if sel.is_displayed(list_tbl):
            _provider = provider
            for _ in paginator.pages():
                for row in list_tbl.rows():
                    if strict:
                        _provider = get_crud(get_provider_key(row.provider.text))
                    servers.append(MiddlewareServer(name=row.server_name.text,
                                                    feed=row.feed.text,
                                                    product=row.product.text,
                                                    provider=_provider))
        return servers

    @classmethod
    def headers(cls):
        sel.force_navigate('middleware_servers')
        headers = [sel.text(hdr).encode("utf-8")
                   for hdr in sel.elements("//thead/tr/th") if hdr.text]
        return headers

    @classmethod
    def servers_in_db(cls, name=None, feed=None, provider=None, strict=True):
        servers = []
        rows = _db_select_query(name=name, feed=feed, provider=provider).all()
        for server in rows:
            if strict:
                _provider = get_crud(get_provider_key(server.provider_name))
            servers.append(MiddlewareServer(name=server.name, hostname=server.hostname,
                                            feed=server.feed, product=server.product,
                                            provider=_provider,
                                            properties=parse_properties(server.properties)))
        return servers

    @classmethod
    def _servers_in_mgmt(cls, provider):
        servers = []
        rows = provider.mgmt.list_server()
        for server in rows:
            servers.append(MiddlewareServer(name=re.sub(r'~~$', '', server.path.resource),
                                            hostname=server.data['Hostname'],
                                            feed=server.path.feed,
                                            product=server.data['Product Name'],
                                            provider=provider))
        return servers

    @classmethod
    def servers_in_mgmt(cls, provider=None):
        if provider is None:
            deployments = []
            for _provider in list_middleware_providers():
                deployments.extend(cls._servers_in_mgmt(get_crud(_provider)))
            return deployments
        else:
            return cls._servers_in_mgmt(provider)

    def _on_detail_page(self):
        """Override existing `_on_detail_page` and return `False` always.
        There is no uniqueness on summary page of this resource.
        Refer: https://github.com/ManageIQ/manageiq/issues/9046
        """
        return False

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            _get_servers_page(self.provider)
            if self.feed:
                list_tbl.click_row_by_cells({'Server Name': self.name, 'Feed': self.feed})
            else:
                list_tbl.click_row_by_cells({'Server Name': self.name})
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def server(self):
        self.summary.reload()
        return self

    @server.variant('mgmt')
    def server_in_mgmt(self):
        db_srv = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if db_srv:
            path = Path(db_srv.ems_ref)
            mgmt_srv = self.provider.mgmt.resource_data(feed_id=path.feed,
                        resource_id=path.resource)
            if mgmt_srv:
                return MiddlewareServer(provider=self.provider,
                                        name=db_srv.name, feed=db_srv.feed,
                                        properties=mgmt_srv.value)
        return None

    @server.variant('db')
    def server_in_db(self):
        server = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if server:
            return MiddlewareServer(provider=self.provider, feed=server.feed, name=server.name,
                                    properties=parse_properties(server.properties))
        return None

    @server.variant('rest')
    def server_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @variable(alias='ui')
    def is_running(self):
        raise NotImplementedError('This feature not implemented yet until issue #9147 is resolved')

    @is_running.variant('db')
    def is_running_in_db(self):
        server = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if not server:
            raise MiddlewareServerNotFound("Server '{}' not found in DB!".format(self.name))
        return parse_properties(server.properties)['Server State'] == 'running'

    @is_running.variant('mgmt')
    def is_running_in_mgmt(self):
        db_srv = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if db_srv:
            path = Path(db_srv.ems_ref)
            mgmt_srv = self.provider.mgmt.resource_data(feed_id=path.feed,
                        resource_id=path.resource)
            if mgmt_srv:
                return mgmt_srv.value['Server State'] == 'running'
        raise MiddlewareServerNotFound("Server '{}' not found in MGMT!".format(self.name))

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
