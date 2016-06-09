import re
from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from mgmtsystem.hawkular import Path
from cfme.middleware import parse_properties
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import nav, toolbar as tb
from utils import attributize_string
from utils.db import cfmedb
from utils.providers import get_crud, get_provider_key
from utils.providers import list_middleware_providers
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, MiddlewareBase, download

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, nativeid=None, server=None, provider=None):
    """Column order: `nativeid`, `name`, `properties`, `server_name`,
    `feed`, `provider_name`, `ems_ref`"""
    t_ms = cfmedb()['middleware_servers']
    t_mds = cfmedb()['middleware_datasources']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_mds.nativeid, t_mds.name, t_mds.properties,
                                   t_ms.name.label('server_name'), t_ms.feed,
                                   t_ems.name.label('provider_name'), t_mds.ems_ref)\
        .join(t_ms, t_mds.server_id == t_ms.id).join(t_ems, t_mds.ems_id == t_ems.id)
    if name:
        query = query.filter(t_mds.name == name)
    if nativeid:
        query = query.filter(t_mds.nativeid == nativeid)
    if server:
        query = query.filter(t_ms.name == server.name)
        if server.feed:
            query = query.filter(t_ms.feed == server.feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    return query


def _get_datasources_page(provider=None, server=None):
    if server:  # if server instance is provided navigate through server page
        server.summary.reload()
        if server.summary.relationships.middleware_datasources.value == 0:
            return
        server.summary.relationships.middleware_datasources.click()
    elif provider:  # if provider instance is provided navigate through provider page
        provider.summary.reload()
        if provider.summary.relationships.middleware_datasources.value == 0:
            return
        provider.summary.relationships.middleware_datasources.click()
    else:  # if None(provider and server) given navigate through all middleware datasources page
        sel.force_navigate('middleware_datasources')


nav.add_branch(
    'middleware_datasources', {
        'middleware_datasource': lambda ctx: list_tbl.select_row('Datasource Name', ctx['name']),
    }
)


class MiddlewareDatasource(MiddlewareBase, Taggable):
    """
    MiddlewareDatasource class provides details on datasource page.
    Class methods available to get existing datasources list

    Args:
        name: Name of the datasource
        provider: Provider object (HawkularProvider)
        nativeid: Native id (internal id) of datasource
        server: Server object of the datasource (MiddlewareServer)
        properties: Datasource driver name, connection URL and JNDI name

    Usage:

        mydatasource = MiddlewareDatasource(name='FooDS',
                                server=ser_instance,
                                provider=haw_provider,
                                properties='ds-properties')

        datasources = MiddlewareDatasource.datasources() [or]
        datasources = MiddlewareDeployment.datasources(provider=haw_provider) [or]
        datasources = MiddlewareDeployment.datasources(provider=haw_provider,server=ser_instance)

    """
    property_tuples = [('name', 'name'), ('nativeid', 'nativeid'),
                       ('driver_name', 'driver_name'), ('jndi_name', 'jndi_name'),
                       ('connection_url', 'connection_url'), ('enabled', 'enabled')]

    def __init__(self, name, server, provider=None, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        if not isinstance(server, MiddlewareServer):
            raise KeyError("'server' should be an instance of MiddlewareServer")
        self.name = name
        self.provider = provider
        self.server = server
        self.nativeid = kwargs['nativeid'] if 'nativeid' in kwargs else None
        if 'properties' in kwargs:
            for property in kwargs['properties']:
                setattr(self, attributize_string(property), kwargs['properties'][property])

    @classmethod
    def datasources(cls, provider=None, server=None):
        datasources = []
        _get_datasources_page(provider=provider, server=server)
        if sel.is_displayed(list_tbl):
            for _ in paginator.pages():
                for row in list_tbl.rows():
                    _server = MiddlewareServer(provider=provider, name=row.server.text)
                    datasources.append(MiddlewareDatasource(provider=provider, server=_server,
                                                            name=row.datasource_name.text))
        return datasources

    @classmethod
    def datasources_in_db(cls, server=None, provider=None, strict=True):
        datasources = []
        rows = _db_select_query(server=server, provider=provider).all()
        _provider = provider
        for datasource in rows:
            if strict:
                _provider = get_crud(get_provider_key(datasource.provider_name))
            _server = MiddlewareServer(name=datasource.server_name, feed=datasource.feed,
                                       provider=provider)
            datasources.append(MiddlewareDatasource(nativeid=datasource.nativeid,
                                            name=datasource.name,
                                            server=_server, provider=_provider,
                                            properties=parse_properties(datasource.properties)))
        return datasources

    @classmethod
    def _datasources_in_mgmt(cls, provider, server=None):
        datasources = []
        rows = provider.mgmt.list_server_datasource()
        for datasource in rows:
            _server = MiddlewareServer(name=re.sub(r'~~$', '', datasource.path.resource[0]),
                                       feed=datasource.path.feed,
                                       provider=provider)
            _include = False
            if server:
                if server.name == _server.name:
                    _include = True if not server.feed else server.feed == _server.feed
            else:
                _include = True
            if _include:
                datasources.append(MiddlewareDatasource(nativeid=datasource.id,
                                                        name=datasource.name,
                                                        server=_server,
                                                        provider=provider))
        return datasources

    @classmethod
    def datasources_in_mgmt(cls, provider=None, server=None):
        if provider is None:
            datasources = []
            for _provider in list_middleware_providers():
                datasources.extend(cls._datasources_in_mgmt(get_crud(_provider), server))
            return datasources
        else:
            return cls._datasources_in_mgmt(provider, server)

    def _on_detail_page(self):
        """Override existing `_on_detail_page` and return `False` always.
        There is no uniqueness on summary page of this resource.
        Refer: https://github.com/ManageIQ/manageiq/issues/9046
        """
        return False

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            _get_datasources_page(provider=self.provider, server=self.server)
            list_tbl.click_row_by_cells({'Datasource Name': self.name, 'Server': self.server.name})
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def datasource(self):
        self.summary.reload()
        self.id = self.summary.properties.nativeid.text_value
        self.server = MiddlewareServer(provider=self.provider,
                                       name=self.summary.relationships.middleware_server.text_value)
        return self

    @datasource.variant('mgmt')
    def datasource_in_mgmt(self):
        db_ds = _db_select_query(name=self.name, server=self.server,
                                 nativeid=self.nativeid).first()
        if db_ds:
            path = Path(db_ds.ems_ref)
            mgmt_ds = self.provider.mgmt.resource_data(feed_id=path.feed,
                        resource_id="{}/{}".format(path.resource[0], path.resource[1]))
            if mgmt_ds:
                ds = MiddlewareDatasource(server=self.server, provider=self.provider,
                                          name=db_ds.name, nativeid=db_ds.nativeid,
                                          properties=mgmt_ds.value)
                return ds
        return None

    @datasource.variant('db')
    def datasource_in_db(self):
        datasource = _db_select_query(name=self.name, server=self.server,
                                      nativeid=self.nativeid).first()
        if datasource:
            _server = MiddlewareServer(name=datasource.server_name, provider=self.provider)
            return MiddlewareDatasource(provider=self.provider, server=_server,
                                    nativeid=datasource.nativeid, name=datasource.name,
                                    properties=parse_properties(datasource.properties))
        return None

    @datasource.variant('rest')
    def datasource_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @classmethod
    def download(cls, extension, provider=None, server=None):
        _get_datasources_page(provider, server)
        download(extension)
