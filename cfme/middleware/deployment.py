from navmazing import NavigateToSibling, NavigateToAttribute

import re
from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.middleware.provider import Deployable
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui import CheckboxTable, paginator, toolbar as tb
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.db import cfmedb
from utils.providers import get_crud_by_name, list_providers_by_class
from utils.varmeth import variable
from cfme.middleware.provider import LIST_TABLE_LOCATOR, MiddlewareBase, download, get_server_name

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, server=None, provider=None):
    """Column order: `id`, `nativeid`, `name`, `server_name`,
    `feed`, `provider_name`, `host_name`, `status`"""
    t_ems = cfmedb()['ext_management_systems']
    t_ms = cfmedb()['middleware_servers']
    t_md = cfmedb()['middleware_deployments']
    query = cfmedb().session.query(
        t_md.id,
        t_md.nativeid.label('nativeid'),
        t_md.name,
        t_ms.name.label('server_name'),
        t_ms.feed.label('feed'),
        t_ems.name.label('provider_name'),
        t_ms.hostname.label('host_name'),
        t_md.status.label('status')) \
        .join(t_ms, t_md.server_id == t_ms.id).join(t_ems, t_md.ems_id == t_ems.id)
    if name:
        query = query.filter(t_md.name == name)
    if server:
        query = query.filter(t_ms.name == server.name)
        if server.feed:
            query = query.filter(t_ms.feed == server.feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    return query


def _get_deployments_page(provider, server):
    if server:  # if server instance is provided navigate through server page
        navigate_to(server, 'ServerDeployments')
    elif provider:  # if provider instance is provided navigate through provider page
        navigate_to(provider, 'ProviderDeployments')
    else:  # if None(provider and server) given navigate through all middleware deployments page
        navigate_to(MiddlewareDeployment, 'All')


class MiddlewareDeployment(MiddlewareBase, Taggable, Navigatable, Deployable):
    """
    MiddlewareDeployment class provides details on deployment page.
    Class methods available to get existing deployments list

    Args:
        name: Name of the deployment
        provider: Provider object (HawkularProvider)
        server: Server object of the deployment (MiddlewareServer)
        nativeid: Native id (internal id) of deployment
        db_id: database row id of deployment

    Usage:

        mydeployment = MiddlewareDeployment(name='Foo.war',
                                server=ser_instance,
                                provider=haw_provider)

        deployments = MiddlewareDeployment.deployments() [or]
        deployments = MiddlewareDeployment.deployments(provider=haw_provider) [or]
        deployments = MiddlewareDeployment.deployments(provider=haw_provider,server=ser_instance)

    """
    property_tuples = [('name', 'Name'), ('status', 'Status')]
    taggable_type = 'MiddlewareDeployment'

    def __init__(self, name, server, provider=None, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        if name is None:
            raise KeyError("'name' should not be 'None'")
        if not isinstance(server, MiddlewareServer):
            raise KeyError("'server' should be an instance of MiddlewareServer")
        self.name = name
        self.server = server
        self.provider = provider
        self.nativeid = kwargs['nativeid'] if 'nativeid' in kwargs else None
        self.hostname = kwargs['hostname'] if 'hostname' in kwargs else None
        self.status = kwargs['status'] if 'status' in kwargs else None
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None

    @classmethod
    def deployments(cls, provider=None, server=None):
        deployments = []
        _get_deployments_page(provider=provider, server=server)
        if sel.is_displayed(list_tbl):
            _provider = provider  # In deployment UI, we cannot get provider name on list all page
            for _ in paginator.pages():
                for row in list_tbl.rows():
                    _server = MiddlewareServer(
                        provider=provider,
                        name=row.server.text,
                        hostname=row.host_name.text)
                    deployments.append(MiddlewareDeployment(
                        provider=_provider,
                        server=_server,
                        name=row.deployment_name.text,
                        hostname=row.host_name.text,
                        status=row.status.text))
        return deployments

    @classmethod
    def deployments_in_db(cls, server=None, provider=None, strict=True):
        deployments = []
        rows = _db_select_query(server=server, provider=provider).all()
        _provider = provider
        for deployment in rows:
            if strict:
                _provider = get_crud_by_name(deployment.provider_name)
            _server = MiddlewareServer(
                name=deployment.server_name,
                feed=deployment.feed,
                provider=provider)
            deployments.append(MiddlewareDeployment(
                nativeid=deployment.nativeid,
                name=deployment.name,
                db_id=deployment.id,
                hostname=deployment.host_name,
                status=deployment.status,
                server=_server,
                provider=_provider))
        return deployments

    @classmethod
    def _deployments_in_mgmt(cls, provider, server=None):
        deployments = []
        rows = provider.mgmt.inventory.list_server_deployment()
        for deployment in rows:
            _server = MiddlewareServer(
                name=get_server_name(deployment.path),
                feed=deployment.path.feed_id,
                provider=provider)
            _include = False
            if server:
                if server.name == _server.name:
                    _include = True if not server.feed else server.feed == _server.feed
            else:
                _include = True
            if _include:
                deployments.append(MiddlewareDeployment(
                    provider=provider,
                    server=_server,
                    nativeid=deployment.id,
                    name=re.sub('((Sub)|Deployment \\[)|(\\])', '', deployment.name)))
        return deployments

    @classmethod
    def deployments_in_mgmt(cls, provider=None, server=None):
        if provider is None:
            deployments = []
            for _provider in list_providers_by_class(HawkularProvider):
                deployments.extend(cls._deployments_in_mgmt(_provider, server))
            return deployments
        else:
            return cls._deployments_in_mgmt(provider, server)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_dep = self.deployment(method='db')
            self.db_id = tmp_dep.db_id
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def deployment(self):
        self.load_details(refresh=False)
        self.id = self.get_detail("Properties", "Nativeid")
        self.status = self.get_detail("Properties", "Status")
        return self

    @deployment.variant('mgmt')
    def deployment_in_mgmt(self):
        raise NotImplementedError('This feature not implemented yet')

    @deployment.variant('db')
    def deployment_in_db(self):
        deployment = _db_select_query(name=self.name, server=self.server,
                                      provider=self.provider).first()
        if deployment:
            _provider = get_crud_by_name(deployment.provider_name)
            _server = MiddlewareServer(
                name=deployment.server_name,
                feed=deployment.feed,
                provider=_provider)
            return MiddlewareDeployment(
                nativeid=deployment.nativeid,
                name=deployment.name,
                hostname=deployment.host_name,
                status=deployment.status,
                server=_server,
                provider=_provider,
                db_id=deployment.id)
        return None

    @deployment.variant('rest')
    def deployment_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @classmethod
    def download(cls, extension, provider=None, server=None):
        _get_deployments_page(provider, server)
        download(extension)


@navigator.register(MiddlewareDeployment, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Deployments')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")


@navigator.register(MiddlewareDeployment, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        list_tbl.click_row_by_cells({'Deployment Name': self.obj.name,
                                     'Server': self.obj.server.name})
