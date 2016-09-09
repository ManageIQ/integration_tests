import re
from cfme.common import Taggable
from cfme.fixtures import pytest_selenium as sel
from cfme.middleware import parse_properties
from cfme.web_ui import CheckboxTable, paginator
from cfme.web_ui.menu import toolbar as tb
from mgmtsystem.hawkular import CanonicalPath
from utils import attributize_string
from utils.db import cfmedb
from utils.varmeth import variable
from . import LIST_TABLE_LOCATOR, MiddlewareBase, download
from cfme.middleware.domain import MiddlewareDomain

list_tbl = CheckboxTable(table_locator=LIST_TABLE_LOCATOR)


def _db_select_query(domain, name=None, feed=None):
    """column order: `id`, `name`, `feed`, `profile`,
    `domain_name`, `ems_ref`, `properties`"""
    t_msgr = cfmedb()['middleware_server_groups']
    t_md = cfmedb()['middleware_domains']
    query = cfmedb().session.query(t_msgr.id, t_msgr.name, t_msgr.feed, t_msgr.profile,
                                   t_md.name.label('domain_name'),
                                   t_msgr.ems_ref, t_msgr.properties)\
        .join(t_md, t_msgr.domain_id == t_md.id)
    if name:
        query = query.filter(t_msgr.name == name)
    if feed:
        query = query.filter(t_msgr.feed == feed)
    query = query.filter(t_md.name == domain.name)
    return query


def _get_server_groups_page(domain):
    domain.summary.reload()
    if domain.summary.relationships.middleware_server_groups.value == 0:
        return
    domain.summary.relationships.middleware_server_groups.click()


class MiddlewareServerGroup(MiddlewareBase, Taggable):
    """
    MiddlewareServerGroup class provides actions and details on Server Group page.
    Class method available to get existing server groups list

    Args:
        name: name of the server group
        domain: Domain (MiddlewareDomain) object to which belongs server group
        profile: Profile of the server group
        feed: feed of the server group
        db_id: database row id of server group

    Usage:

        myservergroup = MiddlewareServerGroup(name='main-server-group', domain=middleware_domain)

        myservergroups = MiddlewareServerGroup.server_groups()

    """
    property_tuples = [('name', 'name'), ('profile', 'profile')]
    taggable_type = 'MiddlewareServerGroup'

    def __init__(self, name, domain, **kwargs):
        if name is None:
            raise KeyError("'name' should not be 'None'")
        self.name = name
        self.domain = domain
        self.profile = kwargs['profile'] if 'profile' in kwargs else None
        self.feed = kwargs['feed'] if 'feed' in kwargs else None
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None
        if 'properties' in kwargs:
            for property in kwargs['properties']:
                # check the properties first, so it will not overwrite core attributes
                if getattr(self, attributize_string(property), None) is None:
                    setattr(self, attributize_string(property), kwargs['properties'][property])

    @classmethod
    def server_groups(cls, domain, strict=True):
        server_groups = []
        _get_server_groups_page(domain=domain)
        if sel.is_displayed(list_tbl):
            _domain = domain
            for _ in paginator.pages():
                for row in list_tbl.rows():
                    if strict:
                        _domain = MiddlewareDomain(row.domain_name.text, provider=domain.provider)
                    server_groups.append(MiddlewareServerGroup(
                        name=row.server_group_name.text,
                        feed=row.feed.text,
                        profile=row.profile.text,
                        provider=domain.provider,
                        domain=_domain))
        return server_groups

    @classmethod
    def server_groups_in_db(cls, domain, name=None, strict=True):
        server_groups = []
        rows = _db_select_query(name=name, domain=domain).all()
        _domain = domain
        for row in rows:
            if strict:
                _domain = MiddlewareDomain(row.domain_name)
            server_groups.append(MiddlewareServerGroup(
                name=row.name,
                feed=row.feed,
                profile=row.profile,
                db_id=row.id,
                provider=domain.provider,
                domain=_domain,
                properties=parse_properties(row.properties)))
        return server_groups

    @classmethod
    def server_groups_in_mgmt(cls, domain):
        server_groups = []

        rows = domain.provider.mgmt.inventory.list_server_group(feed_id=domain.feed)

        for row in rows:
            server_groups.append(MiddlewareServerGroup(
                name=re.sub('(Domain Server Group \\[)|(\\])', '', row.name),
                feed=row.path.feed_id,
                profile=row.data['Profile']
                if 'Profile' in row.data else None,
                domain=domain))
        return server_groups

    @classmethod
    def headers(cls, domain):
        _get_server_groups_page(domain=domain)
        headers = [sel.text(hdr).encode("utf-8")
                   for hdr in sel.elements("//thead/tr/th") if hdr.text]
        return headers

    def _on_detail_page(self):
        """Override existing `_on_detail_page` and return `False` always.
        There is no uniqueness on summary page of this resource.
        Refer: https://github.com/ManageIQ/manageiq/issues/9046
        """
        return False

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            _get_server_groups_page(domain=self.domain)
            if self.feed:
                list_tbl.click_row_by_cells({'Server Group Name': self.name, 'Feed': self.feed})
            else:
                list_tbl.click_row_by_cells({'Server Group Name': self.name})
        if not self.db_id or refresh:
            tmp_sgr = self.server_group(method='db')
            self.db_id = tmp_sgr.db_id
        if refresh:
            tb.refresh()

    @variable(alias='ui')
    def server_group(self):
        self.summary.reload()
        return self

    @server_group.variant('mgmt')
    def server_group_in_mgmt(self):
        db_sgr = _db_select_query(name=self.name, domain=self.domain,
                                 feed=self.feed).first()
        if db_sgr:
            path = CanonicalPath(db_sgr.ems_ref)
            mgmt_sgr = self.domain.provider.mgmt.inventory.get_config_data(
                feed_id=path.feed_id, resource_id=path.resource_id)
            if mgmt_sgr:
                return MiddlewareServerGroup(
                    domain=self.domain,
                    name=db_sgr.name,
                    feed=db_sgr.feed,
                    properties=mgmt_sgr.value)
        return None

    @server_group.variant('db')
    def server_group_in_db(self):
        server_group = _db_select_query(name=self.name, domain=self.domain,
                                 feed=self.feed).first()
        if server_group:
            return MiddlewareServerGroup(
                db_id=server_group.id,
                feed=server_group.feed,
                name=server_group.name,
                profile=server_group.profile,
                domain=self.domain,
                properties=parse_properties(server_group.properties))
        return None

    @server_group.variant('rest')
    def server_group_in_rest(self):
        raise NotImplementedError('This feature not implemented yet')

    @classmethod
    def download(cls, extension, domain):
        _get_server_groups_page(domain)
        download(extension)
