import re

from navmazing import NavigateToSibling
from selenium.common.exceptions import NoSuchElementException
from wrapanapi.hawkular import CanonicalPath

from cfme.common import WidgetasticTaggable
from cfme.exceptions import (MiddlewareDomainNotFound,
                             MiddlewareServerGroupNotFound)
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.provider import MiddlewareBase, download
from cfme.middleware.provider import parse_properties, Container
from cfme.middleware.provider.middleware_views import (ServerGroupDetailsView,
                                                       ServerGroupServerAllView,
                                                       AddDeploymentView)
from cfme.utils import attributize_string
from cfme.utils.appliance import Navigatable, current_appliance
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.varmeth import variable


def _db_select_query(domain, name=None, feed=None):
    """column order: `id`, `name`, `feed`, `profile`,
    `domain_name`, `ems_ref`, `properties`"""
    t_msgr = current_appliance.db.client['middleware_server_groups']
    t_md = current_appliance.db.client['middleware_domains']
    query = current_appliance.db.client.session.query(
        t_msgr.id, t_msgr.name, t_msgr.feed, t_msgr.profile,
        t_md.name.label('domain_name'),
        t_msgr.ems_ref, t_msgr.properties).join(t_md, t_msgr.domain_id == t_md.id)
    if name:
        query = query.filter(t_msgr.name == name)
    if feed:
        query = query.filter(t_msgr.feed == feed)
    query = query.filter(t_md.name == domain.name)
    return query


def _get_server_groups_page(domain):
    return navigate_to(domain, 'DomainServerGroups')


class MiddlewareServerGroup(MiddlewareBase, WidgetasticTaggable, Container, Navigatable):
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
    property_tuples = [('name', 'Name'), ('profile', 'Profile')]
    taggable_type = 'MiddlewareServerGroup'
    deployment_message = 'Deployment "{}" has been initiated on this group.'

    def __init__(self, name, domain, appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
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
        view = _get_server_groups_page(domain=domain)
        _domain = domain
        for _ in view.entities.paginator.pages():
            for row in view.entities.elements:
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
        view = _get_server_groups_page(domain=domain)
        headers = [hdr.encode("utf-8")
                   for hdr in view.entities.elements.headers if hdr]
        return headers

    def load_details(self, refresh=False):
        view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_sgr = self.server_group(method='db')
            self.db_id = tmp_sgr.db_id
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()
        return view

    @variable(alias='ui')
    def server_group(self):
        self.load_details()
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
        view = _get_server_groups_page(domain)
        download(view, extension)

    def restart_server_group(self):
        view = self.load_details()
        view.toolbar.power.item_select('Restart Server Group', handle_alert=True)
        view.flash.assert_success_message('Restart')

    def start_server_group(self):
        view = self.load_details()
        view.toolbar.power.item_select('Start Server Group', handle_alert=True)
        view.flash.assert_success_message('Start')

    def suspend_server_group(self, timeout=10, cancel=False):
        view = self.load_details()
        view.toolbar.power.item_select('Suspend Server Group')
        view.power_operation_form.fill({
            "timeout": timeout,
        })
        view.power_operation_form.cancel_button.click() \
            if cancel else view.power_operation_form.suspend_button.click()
        view.flash.assert_success_message('Suspend initiated for given server group.')

    def resume_server_group(self):
        view = self.load_details()
        view.toolbar.power.item_select('Resume Server Group', handle_alert=True)
        view.flash.assert_success_message('Resume')

    def reload_server_group(self):
        view = self.load_details()
        view.toolbar.power.item_select('Reload Server Group', handle_alert=True)
        view.flash.assert_success_message('Reload')

    def stop_server_group(self, timeout=10, cancel=False):
        view = self.load_details()
        view.toolbar.power.item_select('Stop Server Group')
        view.power_operation_form.fill({
            "timeout": timeout,
        })
        view.power_operation_form.cancel_button.click() \
            if cancel else view.power_operation_form.stop_button.click()
        view.flash.assert_success_message('Stop initiated for given server group.')


@navigator.register(MiddlewareServerGroup, 'Details')
class Details(CFMENavigateStep):
    VIEW = ServerGroupDetailsView

    def prerequisite(self):
        if not self.obj.domain:
            raise MiddlewareDomainNotFound(
                "Middleware Domain is not found in provided Server Group")
        return navigate_to(self.obj.domain, 'DomainServerGroups')

    def step(self):
        try:
            # TODO find_row_on_pages change to entities.get_entity()
            row = self.prerequisite_view.entities.paginator.find_row_on_pages(
                self.prerequisite_view.entities.elements,
                server_group_name=self.obj.name)
        except NoSuchElementException:
            raise MiddlewareServerGroupNotFound(
                "Server Group '{}' not found in table".format(self.obj.name))
        row.click()


@navigator.register(MiddlewareServerGroup, 'ServerGroupServers')
class ServerGroupServers(CFMENavigateStep):
    VIEW = ServerGroupServerAllView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.entities.relationships.click_at('Middleware Servers')


@navigator.register(MiddlewareServerGroup, 'AddDeployment')
class AddDeployment(CFMENavigateStep):
    VIEW = AddDeploymentView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.deployments.item_select('Add Deployment')
