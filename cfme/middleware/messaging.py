import re

from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException

from cfme.common import WidgetasticTaggable, UtilizationMixin
from cfme.exceptions import MiddlewareMessagingNotFound
from cfme.middleware.provider import MiddlewareBase, download, get_server_name
from cfme.middleware.provider import parse_properties
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.provider.middleware_views import (ProviderMessagingAllView,
                                                       MessagingDetailsView)
from cfme.middleware.server import MiddlewareServer
from cfme.utils import attributize_string
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.providers import get_crud_by_name, list_providers_by_class
from cfme.utils.varmeth import variable


def _db_select_query(name=None, nativeid=None, server=None, provider=None):
    """Column order: `id`, `nativeid`, `name`, `properties`, `server_name`,
    `feed`, `provider_name`, `ems_ref`, `messaging_type`"""
    t_ms = current_appliance.db.client['middleware_servers']
    t_mm = current_appliance.db.client['middleware_messagings']
    t_ems = current_appliance.db.client['ext_management_systems']
    query = current_appliance.db.client.session.query(
        t_mm.id,
        t_mm.nativeid,
        t_mm.name,
        t_mm.properties,
        t_ms.name.label('server_name'),
        t_ms.feed,
        t_ems.name.label('provider_name'),
        t_mm.messaging_type,
        t_mm.ems_ref)\
        .join(t_ms, t_mm.server_id == t_ms.id).join(t_ems, t_mm.ems_id == t_ems.id)
    if name:
        query = query.filter(t_mm.name == name)
    if nativeid:
        query = query.filter(t_mm.nativeid == nativeid)
    if server:
        query = query.filter(t_ms.name == server.name)
        if server.feed:
            query = query.filter(t_ms.feed == server.feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    return query


def _get_messagings_page(provider=None, server=None):
    if server:  # if server instance is provided navigate through server page
        return navigate_to(server, 'ServerMessagings')
    elif provider:  # if provider instance is provided navigate through provider page
        return navigate_to(provider, 'ProviderMessagings')
    else:  # if None(provider and server) given navigate through all middleware messagings page
        return navigate_to(MiddlewareMessaging, 'All')


class MiddlewareMessaging(MiddlewareBase, Navigatable, WidgetasticTaggable, UtilizationMixin):
    """
    MiddlewareMessaging class provides details on messaging page.
    Class methods available to get existing messagings list

    Args:
        name: Name of the messaging
        provider: Provider object (HawkularProvider)
        nativeid: Native id (internal id) of messaging
        server: Server object of the messaging (MiddlewareServer)
        properties: Messaging providers
        db_id: database row id of messaging

    Usage:

        mymessaging = MiddlewareMessaging(name='JMS Queue [hawkular/metrics/counters/new]',
                                server=ser_instance,
                                provider=haw_provider,
                                properties='ds-properties')

        messagings = MiddlewareMessaging.messagings() [or]
        messagings = MiddlewareMessaging.messagings(provider=haw_provider) [or]
        messagings = MiddlewareMessaging.messagings(provider=haw_provider,server=ser_instance)

    """
    property_tuples = [('name', 'Name'), ('nativeid', 'Nativeid'),
                       ('messaging_type', 'Messaging type')]
    taggable_type = 'MiddlewareMessaging'

    def __init__(self, name, server, provider=None, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        if name is None:
            raise KeyError("'name' should not be 'None'")
        if not isinstance(server, MiddlewareServer):
            raise KeyError("'server' should be an instance of MiddlewareServer")
        self.name = name
        self.provider = provider
        self.server = server
        self.nativeid = kwargs['nativeid'] if 'nativeid' in kwargs else None
        self.messaging_type = kwargs['messaging_type'] if 'messaging_type' in kwargs else None
        if 'properties' in kwargs:
            for property in kwargs['properties']:
                setattr(self, attributize_string(property), kwargs['properties'][property])
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None

    @classmethod
    def messagings(cls, provider=None, server=None):
        messagings = []
        view = _get_messagings_page(provider=provider, server=server)
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
                _server = MiddlewareServer(provider=provider, name=row.server.text)
                messagings.append(MiddlewareMessaging(
                    provider=provider,
                    server=_server,
                    name=row.messaging_name.text,
                    messaging_type=row.messaging_type.text))
        return messagings

    @classmethod
    def headers(cls):
        view = navigate_to(MiddlewareMessaging, 'All')
        headers = [hdr.encode("utf-8")
                   for hdr in view.entities.elements.headers if hdr]
        return headers

    @classmethod
    def messagings_in_db(cls, server=None, provider=None, strict=True):
        messagings = []
        rows = _db_select_query(server=server, provider=provider).all()
        _provider = provider
        for messaging in rows:
            if strict:
                _provider = get_crud_by_name(messaging.provider_name)
            _server = MiddlewareServer(
                name=messaging.server_name,
                feed=messaging.feed,
                provider=provider)
            messagings.append(MiddlewareMessaging(
                nativeid=messaging.nativeid,
                name=messaging.name,
                db_id=messaging.id,
                server=_server,
                provider=_provider,
                messaging_type=messaging.messaging_type,
                properties=parse_properties(messaging.properties)))
        return messagings

    @classmethod
    def _messagings_in_mgmt(cls, provider, server=None):
        messagings = []
        rows = provider.mgmt.inventory.list_messaging()
        for messaging in rows:
            _server = MiddlewareServer(name=get_server_name(messaging.path),
                                       feed=messaging.path.feed_id,
                                       provider=provider)
            _include = False
            if server:
                if server.name == _server.name:
                    _include = True if not server.feed else server.feed == _server.feed
            else:
                _include = True
            if _include:
                messagings.append(MiddlewareMessaging(nativeid=messaging.id,
                    name=messaging.name,
                    server=_server,
                    provider=provider,
                    messaging_type=re.sub(' \\[.*\\]', '', messaging.name)))
        return messagings

    @classmethod
    def messagings_in_mgmt(cls, provider=None, server=None):
        if provider is None:
            messagings = []
            for _provider in list_providers_by_class(HawkularProvider):
                messagings.extend(cls._messagings_in_mgmt(_provider, server))
            return messagings
        else:
            return cls._messagings_in_mgmt(provider, server)

    def load_details(self, refresh=False):
        view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_msg = self.messaging(method='db')
            self.db_id = tmp_msg.db_id
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()
        return view

    @variable(alias='ui')
    def messaging(self):
        self.load_details(refresh=True)
        self.id = self.get_detail("Properties", "Nativeid")
        self.server = MiddlewareServer(
            provider=self.provider,
            name=self.get_detail("Relationships", "Middleware Server"))
        return self

    @messaging.variant('mgmt')
    def messaging_in_mgmt(self):
        raise NotImplementedError('This feature not implemented yet')

    @messaging.variant('db')
    def messaging_in_db(self):
        messaging = _db_select_query(name=self.name, server=self.server,
            nativeid=self.nativeid).first()
        if messaging:
            _server = MiddlewareServer(name=messaging.server_name, provider=self.provider)
            return MiddlewareMessaging(
                provider=self.provider,
                server=_server,
                db_id=messaging.id,
                nativeid=messaging.nativeid,
                name=messaging.name,
                messaging_type=messaging.messaging_type,
                properties=parse_properties(messaging.properties))
        return None

    @messaging.variant('rest')
    def messaging_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @classmethod
    def download(cls, extension, provider=None, server=None):
        view = _get_messagings_page(provider, server)
        download(view, extension)


@navigator.register(MiddlewareMessaging, 'All')
class All(CFMENavigateStep):
    VIEW = ProviderMessagingAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Middleware', 'Messagings')

    def resetter(self):
        # Reset view and selection
        self.view.entities.paginator.check_all()
        self.view.entities.paginator.uncheck_all()


@navigator.register(MiddlewareMessaging, 'Details')
class Details(CFMENavigateStep):
    VIEW = MessagingDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            if self.obj.server:
                # TODO find_row_on_pages change to entities.get_entity()
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    messaging_name=self.obj.name,
                    server=self.obj.server.name)
            else:
                row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                    self.prerequisite_view.entities.elements,
                    messaging_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareMessagingNotFound(
                "Messaging '{}' not found in table".format(self.obj.name))
        row.click()
