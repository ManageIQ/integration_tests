import re

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic.exceptions import NoSuchElementException
from widgetastic_manageiq import (
    Accordion, BreadCrumb, ItemsToolBarViewSelector, PaginationPane, Table, Text, Search,
    SummaryTable)
from widgetastic_patternfly import BootstrapNav, Button, Dropdown, FlashMessages, Input
from wrapanapi.hawkular import CanonicalPath

from cfme.base.ui import BaseLoggedInPage
from cfme.common import Taggable, UtilizationMixin
from cfme.exceptions import (
    MiddlewareServerNotFound, MiddlewareServerGroupNotFound, MiddlewareDatasourcesNotFound,
    MiddlewareDeploymentsNotFound, MiddlewareMessagingsNotFound)
from cfme.fixtures import pytest_selenium as sel
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.provider import (
    LIST_TABLE_LOCATOR, MiddlewareBase, Container, download, parse_properties)
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.web_ui import CheckboxTable, match_location

from utils import attributize_string
from utils.appliance import Navigatable, current_appliance
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.providers import get_crud_by_name, list_providers_by_class
from utils.varmeth import variable


class ServerToolbar(View):
    """The toolbar on the Server page"""
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ServerDetailsToolbar(View):
    """The toolbar on the Server details page"""
    monitoring = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    power = Dropdown('Power')
    deployments = Dropdown('Deployments')
    jdbc_drivers = Dropdown('JDBC Drivers')
    datasources = Dropdown('Datasources')
    download = Button('Download summary in PDF format')


class ServerGroupDetailsToolbar(View):
    """The toolbar on the server group details page"""
    policy = Dropdown('Policy')
    power = Dropdown('Power')
    deployments = Dropdown('Deployments')
    download = Button('Download summary in PDF format')


class DatasourcesAllToolbar(View):
    """The toolbar on the middleware datasources page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    deployments = Dropdown('Operations')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class DeploymentsAllToolbar(View):
    """The toolbar on the deployments page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    deployments = Dropdown('Operations')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class MessagingsAllToolbar(View):
    """The toolbar on the messagings page"""
    back = Button('Show {} Summary')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ServerDetailsAccordion(View):
    """The accordion on the details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="middleware_server_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="middleware_server_rel"]//ul')


class ServerGroupDetailsAccordion(View):
    """The accordion on the server group details page"""
    @View.nested
    class properties(Accordion):        # noqa
        nav = BootstrapNav('//div[@id="middleware_server_prop"]//ul')

    @View.nested
    class relationships(Accordion):     # noqa
        nav = BootstrapNav('//div[@id="middleware_server_rel"]//ul')


class ServerAllEntities(View):
    """The entities on the all page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ServerDetailsEntities(View):
    """The entities on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ServerGroupDetailsEntities(View):
    """The entities on the server group details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class DatasourcesAllEntities(View):
    """The entities on the datasources all page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class DeploymentsAllEntities(View):
    """The entities on the deployments all page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class MessagingsAllEntities(View):
    """The entities on the messagings all page"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class TimeoutForm(View):
    """The timeout form that pops up"""
    timeout = Input('timeout')
    suspend = Button('Suspend')
    shutdown = Button('Shutdown')
    cancel = Button('Cancel')


class ServerView(BaseLoggedInPage):
    """The base page"""
    @property
    def in_servers(self):
        """Is this section currently being displayed"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Middleware', 'Servers'] and
            # TODO: Needs to be migrated once a Widgetastic version exists
            match_location(controller='middleware_server', title='Middleware Servers'))


class ServerAllView(ServerView):
    """The server list page"""
    toolbar = View.nested(ServerToolbar)
    entities = View.nested(ServerAllEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return self.in_servers and self.entities.title.text == 'Middleware Servers'


class ServerDetailsView(ServerView):
    """The server details page"""
    toolbar = View.nested(ServerDetailsToolbar)
    sidebar = View.nested(ServerDetailsAccordion)
    entities = View.nested(ServerDetailsEntities)
    form = View.nested(TimeoutForm)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_servers and
            self.entities.breadcrumb.active_location == expected_title and
            self.entities.title.text == expected_title)


class ServerGroupDetailsView(ServerView):
    """The server group details page"""
    toolbar = View.nested(ServerGroupDetailsToolbar)
    sidebar = View.nested(ServerGroupDetailsAccordion)
    entities = View.nested(ServerGroupDetailsEntities)

    @property
    def is_displayed(self):
        """IS this page currently being displayed"""
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class DatasourcesAllView(ServerView):
    """The datasources list page"""
    toolbar = View.nested(DatasourcesAllToolbar)
    entities = View.nested(DatasourcesAllEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (All Middleware Datasources)'.format(self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class DeploymentsAllView(ServerView):
    """The deployments list page"""
    toolbar = View.nested(DeploymentsAllToolbar)
    entities = View.nested(DeploymentsAllEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (All Middleware Deployments)'.format(self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


class MessagingsAllView(ServerView):
    """The messagings list page"""
    toolbar = View.nested(MessagingsAllToolbar)
    entities = View.nested(MessagingsAllEntities)
    paginator = View.nested(PaginationPane)

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        expected_title = '{} (All Middleware Messagings)'.format(self.context['object'].name)
        return (
            self.logged_in_as_current_user and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)


list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


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
        view = navigate_to(provider, 'ProviderServers')
    elif server_group:
        # if server group instance is provided navigate through it's servers page
        view = navigate_to(server_group, 'ServerGroupServers')
    else:  # if None(provider) given navigate through all middleware servers page
        view = navigate_to(MiddlewareServer, 'All')
    return view


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
    deployment_message = 'Deployment "{}" has been initiated on this server.'

    def __init__(self, name, provider=None, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.current_view = None
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
        """Return a list of servers"""
        servers = []
        view = _get_servers_page(provider=provider, server_group=server_group)
        if view is not None:
            _provider = provider
            # Go through the rows in the table
            for row in view.entities.table:
                if strict:
                    _provider = get_crud_by_name(row.provider.text)
                servers.append(MiddlewareServer(
                    name=row['Server Name'].text,
                    hostname=row['Host Name'].text,
                    feed=row['Feed'].text,
                    product=row['Product'].text if row['Product'].text else None,
                    provider=_provider))
        elif sel.is_displayed(list_tbl):
            _provider = provider
            from cfme.web_ui import paginator
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
        view = navigate_to(MiddlewareServer, 'All')
        return [hdr for hdr in view.entities.table.headers if hdr is not None]

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
        self.current_view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_ser = self.server(method='db')
            self.db_id = tmp_ser.db_id
        # if refresh:
        #     self.browser.refresh()

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
        view = navigate_to(self, 'ServerGroup')
        return MiddlewareServerGroup(
            provider=self.provider,
            name=view.entities.propeties.get_detail('Name'),
            domain=MiddlewareDomain(
                provider=self.provider,
                name=view.entities.relationships.get_text_of('Middleware Domain')))

    @variable(alias='ui')
    def is_reload_required(self):
        self.load_details(refresh=True)
        return (
            self.current_view.entities.properties.get_text_of('Server State') == 'Reload-required')

    @variable(alias='ui')
    def is_running(self):
        self.load_details(refresh=True)
        return self.current_view.entities.properties.get_text_of('Server State') == 'Running'

    @variable(alias='db')
    def is_suspended(self):
        server = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if not server:
            raise MiddlewareServerNotFound('Server "{}" not found in DB!'.format(self.name))
        return parse_properties(server.properties)['Suspend State'] == 'SUSPENDED'

    @variable(alias='ui')
    def is_starting(self):
        self.load_details(refresh=True)
        return self.current_view.entities.properties.get_text_of('Server State') == 'Starting'

    @variable(alias='ui')
    def is_stopping(self):
        self.load_details(refresh=True)
        return self.current_view.entities.properties.get_text_of('Server State') == 'Stopping'

    @variable(alias='ui')
    def is_stopped(self):
        self.load_details(refresh=True)
        return self.current_view.entities.properties.get_text_of('Server State') == 'Stopped'

    def shutdown_server(self, timeout=10, cancel=False):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.select('Gracefully shutdown Server', handle_alert=True)
        self.current_view.form.fill({'timeout': timeout})
        self.current_view.form.cancel.click() if cancel else self.current_view.form.shutdown.click()
        self.current_view.entities.flash.assert_success_message(
            'Shutdown initiated for selected server(s)')

    def restart_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Restart Server', handle_alert=True)
        self.current_view.entities.flash.assert_success_message(
            'Restart initiated for selected server(s)')

    def start_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Start Server', handle_alert=True)
        self.current_view.entities.flash.assert_success_message(
            'Start initiated for selected server(s)')

    def suspend_server(self, timeout=10, cancel=False):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Suspend Server')
        self.current_view.form.fill({'timeout': timeout})
        self.current_view.form.cancel.click() if cancel else self.current_view.form.suspend.click()
        self.current_view.entities.flash.assert_success_message(
            'Suspend initiated for selected server(s)')

    def resume_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Resume Server', handle_alert=True)
        self.current_view.entities.flash.assert_success_message(
            'Resume initiated for selected server(s)')

    def reload_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Reload Server', handle_alert=True)
        self.current_view.entities.flash.assert_success_message(
            'Reload initiated for selected server(s)')

    def stop_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Stop Server', handle_alert=True)
        self.current_view.entities.flash.assert_success_message(
            'Stop initiated for selected server(s)')

    def kill_server(self):
        self.load_details(refresh=True)
        self.current_view.toolbar.power.item_select('Kill Server', handle_alert=True)

    def is_immutable(self):
        view = navigate_to(self, 'Details')
        return not (view.toolbar.power.is_displayed or
                    view.toolbar.deployments.is_displayed or
                    view.toolbar.jdbc_drivers.is_displayed or
                    view.toolbar.datasources.is_displayed)

    @classmethod
    def download(cls, extension, provider=None, server_group=None):
        _get_servers_page(provider, server_group)
        download(extension)


@navigator.register(MiddlewareServer, 'All')
class All(CFMENavigateStep):
    VIEW = ServerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Navigate to the page"""
        self.prerequisite_view.navigation.select('Middleware', 'Servers')

    def resetter(self):
        """Reset view and selection"""
        self.view.toolbar.view_selector.select('List View')
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(MiddlewareServer, 'Details')
class Details(CFMENavigateStep):
    VIEW = ServerDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        """Navigate to the item"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            if self.obj.feed:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table,
                    server_name=self.obj.name, feed=self.obj.feed)
            elif self.obj.hostname:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table,
                    server_name=self.obj.name, host_name=self.obj.hostname)
            else:
                row = self.prerequisite_view.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.table, server_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareServerNotFound('Middleware server {} not found'.format(self.obj.name))
        row.click()


@navigator.register(MiddlewareServer, 'ServerDatasources')
class ServerDatasources(CFMENavigateStep):
    VIEW = DatasourcesAllView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.sidebar.relationships.open()
            self.prerequisite_view.sidebar.relationships.nav.select(
                title='Show Middleware Datasources')
        except NoSuchElementException:
            raise MiddlewareDatasourcesNotFound(
                'Server {} does not have Datasources'.format(self.obj.name))


@navigator.register(MiddlewareServer, 'ServerDeployments')
class ServerDeployments(CFMENavigateStep):
    VIEW = DeploymentsAllView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.sidebar.relationships.open()
            self.prerequisite_view.sidebar.relationships.nav.select(
                title='Show Middleware Deployments')
        except NoSuchElementException:
            raise MiddlewareDeploymentsNotFound(
                'Server {} does not have Deployments'.format(self.obj.name))


@navigator.register(MiddlewareServer, 'ServerMessagings')
class ServerMessagings(CFMENavigateStep):
    VIEW = MessagingsAllView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.sidebar.relationships.open()
            self.prerequisite_view.sidebar.relationships.nav.select(
                title='Show Middleware Messagings')
        except NoSuchElementException:
            raise MiddlewareMessagingsNotFound(
                'Server {} does not have Messagings'.format(self.obj.name))


@navigator.register(MiddlewareServer, 'ServerGroup')
class ServerGroup(CFMENavigateStep):
    VIEW = ServerGroupDetailsView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        try:
            self.prerequisite_view.sidebar.relationships.open()
            self.prerequisite_view.sidebar.relationships.nav.select(
                title='Show this Middleware Server\'s parent Middleware Server Group')
        except NoSuchElementException:
            raise MiddlewareServerGroupNotFound(
                'Server {} does not belong to Server Group'.format(self.obj.name))
