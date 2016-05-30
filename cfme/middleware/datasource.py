import re
from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import nav, toolbar as tb
from utils.db import cfmedb
from . import LIST_TABLE_LOCATOR, MiddlewareBase

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, server=None, provider=None):
    t_ms = cfmedb()['middleware_servers']
    t_mds = cfmedb()['middleware_datasources']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_mds.nativeid, t_mds.name,
                                   t_mds.ems_ref, t_ms.name, t_ems.name,
                                   t_mds.properties).join(t_ms,
                                            t_mds.server_id == t_ms.id).join(t_ems,
                                            t_mds.ems_id == t_ems.id)
    if name:
        query = query.filter(t_mds.name == name)
    if server:
        query = query.filter(t_mds.nativeid.like('%{}%'.format(server)))
    if provider:
        query = query.filter(t_ems.name == provider)
    return query

nav.add_branch(
    'middleware_datasources', {
        'middleware_datasource': lambda ctx: list_tbl.select_row('Datasource Name', ctx['name']),
        'middleware_datasource_detail':
            lambda ctx: list_tbl.click_row_by_cells({'Datasource Name': ctx['name']}),
    }
)


class MiddlewareDatasource(MiddlewareBase, Taggable):
    """
    MiddlewareDatasource class provides details on datasource page.
    Class methods available to get existing datasources list

    Args:
        name: Name of the datasource
        provider: Provider object (HawkularProvider)
        id: Native id (internal id) of datasource
        server: Server name of the datasource
        properties: Datasource driver name, connection URL and JNDI name

    Usage:

        mydatasource = MiddlewareDatasource(name='Foo.war',
                                server='Bar-serv',
                                provider=haw_provider,
                                properties='ds-properties')

        datasources = MiddlewareDatasource.datasources()

    """
    property_tuples = [('name', 'name')]

    def __init__(self, name, provider=None, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.id = kwargs['id'] if 'id' in kwargs else None
        self.server = kwargs['server'] if 'server' in kwargs else None
        self.properties = kwargs['properties'] if 'properties' in kwargs else None

    @classmethod
    def datasources(cls, provider=None):
        datasources = []
        if provider:
            # if provider instance is provided try to navigate provider's datasources page
            # if no datasources are registered in provider, returns empty list
            if not provider.load_all_provider_datasources():
                return []
        else:
            # if provider instance is not provided then navigates  to all datasources page
            sel.force_navigate('middleware_datasources')
        if sel.is_displayed(list_tbl):
            for page in paginator.pages():
                for row in list_tbl.rows():
                    datasources.append(MiddlewareDatasource(name=row.datasource_name.text,
                                                            server=row.server.text))
        return datasources

    @classmethod
    def datasources_in_db(cls, server=None, provider=None):
        datasources = []
        rows = _db_select_query(server=server, provider=(provider.name if provider else None)).all()
        for datasource in rows:
            datasources.append(MiddlewareDatasource(id=datasource[0], name=datasource[1],
                                                    server=datasource[3], provider=datasource[4],
                                                    properties=datasource[5]))
        return datasources

    @classmethod
    def datasources_in_mgmt(cls, provider):
        datasources = []
        rows = provider.mgmt.list_server_datasource()
        for datasource in rows:
            datasources.append(MiddlewareDatasource(provider=provider.name,
                    id=datasource.id, name=datasource.name,
                    server=re.sub(r'~~$', '', datasource.path.resource[0])))
        return datasources

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            sel.force_navigate('middleware_datasource_detail', context={'name': self.name})
        if refresh:
            tb.refresh()
