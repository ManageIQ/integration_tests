import re

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException
from wrapanapi.hawkular import CanonicalPath

from cfme.common import WidgetasticTaggable, UtilizationMixin
from cfme.exceptions import MiddlewareServerNotFound, \
    MiddlewareServerGroupNotFound
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.provider import (
    MiddlewareBase, download
)
from cfme.middleware.provider import (parse_properties, Container, Reportable)
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.provider.middleware_views import (ServerAllView,
    ServerDetailsView, ServerDatasourceAllView, ServerDeploymentAllView,
    ServerMessagingAllView, ServerGroupDetailsView, AddDatasourceView,
    AddJDBCDriverView, AddDeploymentView)
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.utils import attributize_string
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.providers import get_crud_by_name, list_providers_by_class
from cfme.utils.varmeth import variable


def _db_select_query(name=None, feed=None, provider=None, server_group=None,
                     product=None):
    """column order: `id`, `name`, `hostname`, `feed`, `product`,
    `provider_name`, `ems_ref`, `properties`, `server_group_name`"""
    t_ms = current_appliance.db.client['middleware_servers']
    t_msgr = current_appliance.db.client['middleware_server_groups']
    t_ems = current_appliance.db.client['ext_management_systems']
    query = current_appliance.db.client.session.query(
        t_ms.id, t_ms.name, t_ms.hostname, t_ms.feed, t_ms.product,
        t_ems.name.label('provider_name'),
        t_ms.ems_ref, t_ms.properties,
        t_msgr.name.label('server_group_name'))\
        .join(t_ems, t_ms.ems_id == t_ems.id)\
        .outerjoin(t_msgr, t_ms.server_group_id == t_msgr.id)
    if name:
        query = query.filter(t_ms.name == name)
    if feed:
        query = query.filter(t_ms.feed == feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    if server_group:
        query = query.filter(t_msgr.name == server_group.name)
        query = query.filter(t_msgr.feed == server_group.feed)
    if product:
        query = query.filter(t_ms.product == product)
    return query


def _get_servers_page(provider=None, server_group=None):
    if provider:  # if provider instance is provided navigate through provider's servers page
        return navigate_to(provider, 'ProviderServers')
    elif server_group:
        # if server group instance is provided navigate through it's servers page
        return navigate_to(server_group, 'ServerGroupServers')
    else:  # if None(provider) given navigate through all middleware servers page
        return navigate_to(MiddlewareServer, 'All')


class MiddlewareServer(MiddlewareBase, WidgetasticTaggable, Container, Reportable,
                       Navigatable, UtilizationMixin):
    """
    MiddlewareServer class provides actions and details on Server page.
    Class method available to get existing servers list

    Args:
        name: name of the server
        hostname: Host name of the server
        provider: Provider object (HawkularProvider)
        product: Product type of the server
        feed: feed of the server
        db_id: database row id of server

    Usage:

        myserver = MiddlewareServer(name='Foo.war', provider=haw_provider)
        myserver.reload_server()

        myservers = MiddlewareServer.servers()

    """
    property_tuples = [('name', 'Name'), ('feed', 'Feed'),
                       ('bound_address', 'Bind Address')]
    taggable_type = 'MiddlewareServer'
    deployment_message = 'Deployment "{}" has been initiated on this server.'

    def __init__(self, name, provider=None, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.product = kwargs['product'] if 'product' in kwargs else None
        self.hostname = kwargs['hostname'] if 'hostname' in kwargs else None
        self.feed = kwargs['feed'] if 'feed' in kwargs else None
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None
        if 'properties' in kwargs:
            for prop in kwargs['properties']:
                # check the properties first, so it will not overwrite core attributes
                if getattr(self, attributize_string(prop), None) is None:
                    setattr(self, attributize_string(prop), kwargs['properties'][prop])

    @classmethod
    def servers(cls, provider=None, server_group=None, strict=True):
        servers = []
        view = _get_servers_page(provider=provider, server_group=server_group)
        _provider = provider  # In deployment UI, we cannot get provider name on list all page
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
                if strict:
                    _provider = get_crud_by_name(row.provider.text)
                servers.append(MiddlewareServer(
                    name=row.server_name.text,
                    feed=row.feed.text,
                    hostname=row.host_name.text,
                    product=row.product.text
                    if row.product.text else None,
                    provider=_provider))
        return servers

    @classmethod
    def headers(cls):
        view = navigate_to(MiddlewareServer, 'All')
        headers = [hdr.encode("utf-8")
                   for hdr in view.entities.elements.headers if hdr]
        return headers

    @classmethod
    def servers_in_db(cls, name=None, feed=None, provider=None, product=None,
                      server_group=None, strict=True):
        servers = []
        rows = _db_select_query(name=name, feed=feed, provider=provider,
            product=product, server_group=server_group).all()
        _provider = provider
        for server in rows:
            if strict:
                _provider = get_crud_by_name(server.provider_name)
            servers.append(MiddlewareServer(
                name=server.name,
                hostname=server.hostname,
                feed=server.feed,
                product=server.product,
                db_id=server.id,
                provider=_provider,
                properties=parse_properties(server.properties)))
        return servers

    @classmethod
    def _servers_in_mgmt(cls, provider, server_group=None):
        servers = []
        rows = provider.mgmt.inventory.list_server(feed_id=server_group.feed
                                        if server_group else None)
        for row in rows:
            server = MiddlewareServer(
                name=re.sub('(Domain )|(WildFly Server \\[)|(\\])', '', row.name),
                hostname=row.data['Hostname']
                if 'Hostname' in row.data else None,
                feed=row.path.feed_id,
                product=row.data['Product Name']
                if 'Product Name' in row.data else None,
                provider=provider)
            # if server_group is given, filter those servers which belongs to it
            if not server_group or cls._belongs_to_group(server, server_group):
                servers.append(server)
        return servers

    @classmethod
    def servers_in_mgmt(cls, provider=None, server_group=None):
        if provider is None:
            servers = []
            for _provider in list_providers_by_class(HawkularProvider):
                servers.extend(cls._servers_in_mgmt(_provider, server_group))
            return servers
        else:
            return cls._servers_in_mgmt(provider, server_group)

    @classmethod
    def _belongs_to_group(cls, server, server_group):
        server_mgmt = server.server(method='mgmt')
        return getattr(server_mgmt, attributize_string('Server Group'), None) == server_group.name

    def load_details(self, refresh=False):
        view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_ser = self.server(method='db')
            self.db_id = tmp_ser.db_id
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()
        return view

    @variable(alias='ui')
    def server(self):
        self.load_details(refresh=False)
        return self

    @server.variant('mgmt')
    def server_in_mgmt(self):
        db_srv = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if db_srv:
            path = CanonicalPath(db_srv.ems_ref)
            mgmt_srv = self.provider.mgmt.inventory.get_config_data(feed_id=path.feed_id,
                                                                    resource_id=path.resource_id)
            if mgmt_srv:
                return MiddlewareServer(
                    provider=self.provider,
                    name=db_srv.name, feed=db_srv.feed,
                    properties=mgmt_srv.value)
        return None

    @server.variant('db')
    def server_in_db(self):
        server = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if server:
            return MiddlewareServer(
                db_id=server.id, provider=self.provider,
                feed=server.feed, name=server.name,
                hostname=server.hostname,
                properties=parse_properties(server.properties))
        return None

    @server.variant('rest')
    def server_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @variable(alias='ui')
    def server_group(self):
        self.load_details()
        return MiddlewareServerGroup(
            provider=self.provider,
            name=self.get_detail("Properties", "Name"),
            domain=MiddlewareDomain(
                provider=self.provider,
                name=self.get_detail("Relationships", "Middleware Domain")))

    @variable(alias='ui')
    def is_reload_required(self):
        self.load_details(refresh=True)
        return self.get_detail("Properties", "Server State") == 'Reload-required'

    @variable(alias='ui')
    def is_running(self):
        self.load_details(refresh=True)
        return self.get_detail("Properties", "Server State") == 'Running'

    @variable(alias='db')
    def is_suspended(self):
        server = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if not server:
            raise MiddlewareServerNotFound("Server '{}' not found in DB!".format(self.name))
        return parse_properties(server.properties)['Suspend State'] == 'SUSPENDED'

    @variable(alias='ui')
    def is_starting(self):
        self.load_details(refresh=True)
        return self.get_detail("Properties", "Server State") == 'Starting'

    @variable(alias='ui')
    def is_stopping(self):
        self.load_details(refresh=True)
        return self.get_detail("Properties", "Server State") == 'Stopping'

    @variable(alias='ui')
    def is_stopped(self):
        self.load_details(refresh=True)
        return self.get_detail("Properties", "Server State") == 'Stopped'

    def shutdown_server(self, timeout=10, cancel=False):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Gracefully shutdown Server')
        view.power_operation_form.fill({
            "timeout": timeout,
        })
        if cancel:
            view.power_operation_form.cancel_button.click()
        else:
            view.power_operation_form.shutdown_button.click()
            view.flash.assert_success_message('Shutdown initiated for selected server(s)')

    def restart_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Restart Server', handle_alert=True)
        view.flash.assert_success_message('Restart initiated for selected server(s)')

    def start_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Start Server', handle_alert=True)
        view.assert_success_message('Start initiated for selected server(s)')

    def suspend_server(self, timeout=10, cancel=False):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Suspend Server')
        view.power_operation_form.fill({
            "timeout": timeout,
        })
        if cancel:
            view.power_operation_form.cancel_button.click()
        else:
            view.power_operation_form.suspend_button.click()
            view.flash.assert_success_message('Suspend initiated for selected server(s)')

    def resume_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Resume Server', handle_alert=True)
        view.flash.assert_success_message('Resume initiated for selected server(s)')

    def reload_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Reload Server', handle_alert=True)
        view.flash.assert_success_message('Reload initiated for selected server(s)')

    def stop_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Stop Server', handle_alert=True)
        view.flash.assert_success_message('Stop initiated for selected server(s)')

    def kill_server(self):
        view = self.load_details(refresh=True)
        view.toolbar.power.item_select('Kill Server', handle_alert=True)
        view.flash.assert_success_message('Kill initiated for selected server(s)')

    @classmethod
    def download(cls, extension, provider=None, server_group=None):
        view = _get_servers_page(provider, server_group)
        download(view, extension)


@navigator.register(MiddlewareServer, 'All')
class All(CFMENavigateStep):
    VIEW = ServerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Servers')


@navigator.register(MiddlewareServer, 'Details')
class Details(CFMENavigateStep):
    VIEW = ServerDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        try:
            if self.obj.feed:
                # TODO find_row_on_pages change to entities.get_entity()
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    server_name=self.obj.name, feed=self.obj.feed)
            elif self.obj.hostname:
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    server_name=self.obj.name, host_name=self.obj.hostname)
            else:
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements, server_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareServerNotFound(
                "Server '{}' not found in table".format(self.obj.name))
        row.click()


@navigator.register(MiddlewareServer, 'ServerDatasources')
class ServerDatasources(CFMENavigateStep):
    VIEW = ServerDatasourceAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Datasources')


@navigator.register(MiddlewareServer, 'ServerDeployments')
class ServerDeployments(CFMENavigateStep):
    VIEW = ServerDeploymentAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Deployments')


@navigator.register(MiddlewareServer, 'ServerMessagings')
class ServerMessagings(CFMENavigateStep):
    VIEW = ServerMessagingAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Messagings')


@navigator.register(MiddlewareServer, 'ServerGroup')
class ServerGroup(CFMENavigateStep):
    VIEW = ServerGroupDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        try:
            self.prerequisite_view.entities.relationships.click_at('Middleware Server Group')
        except NoSuchElementException:
            raise MiddlewareServerGroupNotFound('Server does not belong to Server Group')


@navigator.register(MiddlewareServer, 'AddDatasource')
class AddDatasource(CFMENavigateStep):
    VIEW = AddDatasourceView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.datasources.item_select('Add Datasource')


@navigator.register(MiddlewareServer, 'AddJDBCDriver')
class AddJDBCDriver(CFMENavigateStep):
    VIEW = AddJDBCDriverView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.drivers.item_select('Add JDBC Driver')


@navigator.register(MiddlewareServer, 'AddDeployment')
class AddDeployment(CFMENavigateStep):
    VIEW = AddDeploymentView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.deployments.item_select('Add Deployment')
