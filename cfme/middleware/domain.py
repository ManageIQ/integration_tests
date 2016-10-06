from navmazing import NavigateToSibling, NavigateToAttribute
from cfme.common import Taggable
from cfme.exceptions import MiddlewareDomainNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.middleware import parse_properties
from cfme.web_ui import CheckboxTable, paginator, InfoBlock
from cfme.web_ui.menu import toolbar as tb
from mgmtsystem.hawkular import CanonicalPath
from utils import attributize_string
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.db import cfmedb
from utils.providers import get_crud, get_provider_key, list_providers
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, MiddlewareBase, download

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(name=None, feed=None, provider=None):
    """column order: `id`, `name`, `feed`,
    `provider_name`, `ems_ref`, `properties`"""
    t_md = cfmedb()['middleware_domains']
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_md.id, t_md.name, t_md.feed,
                                   t_ems.name.label('provider_name'),
                                   t_md.ems_ref, t_md.properties)\
        .join(t_ems, t_md.ems_id == t_ems.id)
    if name:
        query = query.filter(t_md.name == name)
    if feed:
        query = query.filter(t_md.feed == feed)
    if provider:
        query = query.filter(t_ems.name == provider.name)
    return query


def _get_domains_page(provider):
    if provider:  # if provider instance is provided navigate through provider's domains page
        navigate_to(provider, 'ProviderDomains')
    else:  # if None(provider) given navigate through all middleware domains page
        navigate_to(MiddlewareDomain, 'All')


class MiddlewareDomain(MiddlewareBase, Navigatable, Taggable):
    """
    MiddlewareDomain class provides actions and details on Domain page.
    Class method available to get existing domains list

    Args:
        name: name of the domain
        provider: Provider object (HawkularProvider)
        product: Product type of the domain
        feed: feed of the domain
        db_id: database row id of domain

    Usage:

        mydomain = MiddlewareDomain(name='master', provider=haw_provider)

        mydomains = MiddlewareDomain.domains()

    """
    property_tuples = [('name', 'Name')]
    taggable_type = 'MiddlewareDomain'

    def __init__(self, name, provider=None, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.provider = provider
        self.product = kwargs['product'] if 'product' in kwargs else None
        self.feed = kwargs['feed'] if 'feed' in kwargs else None
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None
        if 'properties' in kwargs:
            for property in kwargs['properties']:
                # check the properties first, so it will not overwrite core attributes
                if getattr(self, attributize_string(property), None) is None:
                    setattr(self, attributize_string(property), kwargs['properties'][property])

    @classmethod
    def domains(cls, provider=None, strict=True):
        domains = []
        _get_domains_page(provider=provider)
        if sel.is_displayed(list_tbl):
            _provider = provider
            for _ in paginator.pages():
                for row in list_tbl.rows():
                    if strict:
                        _provider = get_crud(get_provider_key(row.provider.text))
                    domains.append(MiddlewareDomain(
                        name=row.domain_name.text,
                        feed=row.feed.text,
                        provider=_provider))
        return domains

    @classmethod
    def headers(cls):
        sel.force_navigate('middleware_domains')
        headers = [sel.text(hdr).encode("utf-8")
                   for hdr in sel.elements("//thead/tr/th") if hdr.text]
        return headers

    @classmethod
    def domains_in_db(cls, name=None, feed=None, provider=None, strict=True):
        domains = []
        rows = _db_select_query(name=name, feed=feed, provider=provider).all()
        _provider = provider
        for domain in rows:
            if strict:
                _provider = get_crud(get_provider_key(domain.provider_name))
            domains.append(MiddlewareDomain(
                name=domain.name,
                feed=domain.feed,
                db_id=domain.id,
                provider=_provider,
                properties=parse_properties(domain.properties)))
        return domains

    @classmethod
    def _domains_in_mgmt(cls, provider):
        domains = []
        rows = provider.mgmt.inventory.list_domain()
        for row in rows:
            domains.append(MiddlewareDomain(
                name=row.data['Local Host Name'],
                feed=row.path.feed_id,
                product=row.data['Product Name']
                if 'Product Name' in row.data else None,
                provider=provider))
        return domains

    @classmethod
    def domains_in_mgmt(cls, provider=None):
        if provider is None:
            deployments = []
            for _provider in list_providers('hawkular'):
                deployments.extend(cls._domains_in_mgmt(get_crud(_provider)))
            return deployments
        else:
            return cls._domains_in_mgmt(provider)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_dmn = self.domain(method='db')
            self.db_id = tmp_dmn.db_id
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def domain(self):
        self.load_details(refresh=True)
        return self

    @domain.variant('mgmt')
    def domain_in_mgmt(self):
        db_dmn = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if db_dmn:
            path = CanonicalPath(db_dmn.ems_ref)
            mgmt_dmn = self.provider.mgmt.inventory.get_config_data(feed_id=path.feed_id,
                        resource_id=path.resource_id)
            if mgmt_dmn:
                return MiddlewareDomain(
                    provider=self.provider,
                    name=db_dmn.name, feed=db_dmn.feed,
                    properties=mgmt_dmn.value)
        return None

    @domain.variant('db')
    def domain_in_db(self):
        domain = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if domain:
            return MiddlewareDomain(
                db_id=domain.id, provider=self.provider,
                feed=domain.feed, name=domain.name,
                properties=parse_properties(domain.properties))
        return None

    @domain.variant('rest')
    def domain_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @variable(alias='ui')
    def is_running(self):
        raise NotImplementedError('This feature not implemented yet')

    @is_running.variant('db')
    def is_running_in_db(self):
        domain = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if not domain:
            raise MiddlewareDomainNotFound("Domain '{}' not found in DB!".format(self.name))
        return parse_properties(domain.properties)['Host State'] == 'running'

    @is_running.variant('mgmt')
    def is_running_in_mgmt(self):
        db_dmn = _db_select_query(name=self.name, provider=self.provider,
                                 feed=self.feed).first()
        if db_dmn:
            path = CanonicalPath(db_dmn.ems_ref)
            mgmt_dmn = self.provider.mgmt.inventory.get_config_data(feed_id=path.feed_id,
                                                                    resource_id=path.resource_id)
            if mgmt_dmn:
                return mgmt_dmn.value['Domain State'] == 'running'
        raise MiddlewareDomainNotFound("Domain '{}' not found in MGMT!".format(self.name))

    @classmethod
    def download(cls, extension, provider=None):
        _get_domains_page(provider)
        download(extension)


@navigator.register(MiddlewareDomain, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Middleware', 'Domains')(None)

    def resetter(self):
        # Reset view and selection
        tb.select("List View")


@navigator.register(MiddlewareDomain, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        if self.obj.feed:
            list_tbl.click_row_by_cells({'Domain Name': self.obj.name,
                                         'Feed': self.obj.feed})
        else:
            list_tbl.click_row_by_cells({'Domain Name': self.obj.name})


@navigator.register(MiddlewareDomain, 'DomainServerGroups')
class DomainServerGroups(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Server Groups'))
