import re
from cfme.common import Taggable, UtilizationMixin
from cfme.exceptions import MiddlewareServerNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.middleware.provider import parse_properties, Container
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.web_ui import (
    CheckboxTable, paginator, Form, Input, fill, InfoBlock
)
from cfme.web_ui.form_buttons import FormButton
from cfme.web_ui import toolbar as tb
from mgmtsystem.hawkular import CanonicalPath
from navmazing import NavigateToSibling, NavigateToAttribute
from utils import attributize_string
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.db import cfmedb
from utils.providers import get_crud_by_name, list_providers_by_class
from utils.varmeth import variable
from cfme.middleware.provider import LIST_TABLE_LOCATOR, pwr_btn, MiddlewareBase, download

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, feed=None, provider=None, server_group=None,
                     product=None):
    """column order: `id`, `name`, `hostname`, `feed`, `product`,
    `provider_name`, `ems_ref`, `properties`, `server_group_name`"""
    t_ms = cfmedb()['middleware_servers']
    t_msgr = cfmedb()['middleware_server_groups']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_ms.id, t_ms.name, t_ms.hostname, t_ms.feed, t_ms.product,
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
    if product:
        query = query.filter(t_ms.product == product)
    return query


def _get_servers_page(provider=None, server_group=None):
    if provider:  # if provider instance is provided navigate through provider's servers page
        navigate_to(provider, 'ProviderServers')
    elif server_group:
        # if server group instance is provided navigate through it's servers page
        navigate_to(server_group, 'ServerGroupServers')
    else:  # if None(provider) given navigate through all middleware servers page
        navigate_to(MiddlewareServer, 'All')


timeout_form = Form(
    fields=[
        ("timeout", Input("timeout", use_id=True)),
        ('suspend_button', FormButton("Suspend")),
        ('shutdown_button', FormButton("Shutdown")),
        ('cancel_button', FormButton("Cancel"))
    ]
)


class MiddlewareServer(MiddlewareBase, Taggable, Container, Navigatable, UtilizationMixin):
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
            for property in kwargs['properties']:
                # check the properties first, so it will not overwrite core attributes
                if getattr(self, attributize_string(property), None) is None:
                    setattr(self, attributize_string(property), kwargs['properties'][property])

    @classmethod
    def servers(cls, provider=None, server_group=None, strict=True):
        servers = []
        _get_servers_page(provider=provider, server_group=server_group)
        if sel.is_displayed(list_tbl):
            _provider = provider
            for _ in paginator.pages():
                for row in list_tbl.rows():
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
        navigate_to(MiddlewareServer, 'All')
        headers = [sel.text(hdr).encode("utf-8")
                   for hdr in sel.elements("//thead/tr/th") if hdr.text]
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
        navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_ser = self.server(method='db')
            self.db_id = tmp_ser.db_id
        if refresh:
            tb.refresh()

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
        self.load_details(refresh=True)
        pwr_btn("Gracefully shutdown Server", invokes_alert=True)
        fill(
            timeout_form,
            {"timeout": timeout},
        )
        sel.click(timeout_form.cancel_button if cancel else timeout_form.shutdown_button)

    def restart_server(self):
        self.load_details(refresh=True)
        pwr_btn("Restart Server", invokes_alert=True)
        sel.handle_alert()

    def start_server(self):
        self.load_details(refresh=True)
        pwr_btn("Start Server", invokes_alert=True)
        sel.handle_alert()

    def suspend_server(self, timeout=10, cancel=False):
        self.load_details(refresh=True)
        pwr_btn("Suspend Server", invokes_alert=True)
        fill(
            timeout_form,
            {"timeout": timeout},
        )
        sel.click(timeout_form.cancel_button if cancel else timeout_form.suspend_button)

    def resume_server(self):
        self.load_details(refresh=True)
        pwr_btn("Resume Server", invokes_alert=True)
        sel.handle_alert()

    def reload_server(self):
        self.load_details(refresh=True)
        pwr_btn("Reload Server", invokes_alert=True)
        sel.handle_alert()

    def stop_server(self):
        self.load_details(refresh=True)
        pwr_btn("Stop Server", invokes_alert=True)
        sel.handle_alert()

    def kill_server(self):
        self.load_details(refresh=True)
        pwr_btn("Kill Server", invokes_alert=True)
        sel.handle_alert()

    @classmethod
    def download(cls, extension, provider=None, server_group=None):
        _get_servers_page(provider, server_group)
        download(extension)


@navigator.register(MiddlewareServer, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Servers')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")


@navigator.register(MiddlewareServer, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        if self.obj.feed:
            list_tbl.click_row_by_cells({'Server Name': self.obj.name,
                                         'Feed': self.obj.feed})
        elif self.obj.hostname:
            list_tbl.click_row_by_cells({'Server Name': self.obj.name,
                                         'Host Name': self.obj.hostname})
        else:
            list_tbl.click_row_by_cells({'Server Name': self.obj.name})


@navigator.register(MiddlewareServer, 'ServerDatasources')
class ServerDatasources(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Datasources'))


@navigator.register(MiddlewareServer, 'ServerDeployments')
class ServerDeployments(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Deployments'))


@navigator.register(MiddlewareServer, 'ServerMessagings')
class ServerMessagings(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Messagings'))
