from navmazing import NavigateToSibling, NavigateToAttribute

from cfme.common.provider import import_all_modules_of
from cfme.common.provider import BaseProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Form, AngularSelect, InfoBlock, Input, Quadicon,
    form_buttons, toolbar as tb, paginator
)
from utils import version
from utils.appliance.implementations.ui import navigator, CFMENavigateStep
from utils.db import cfmedb

from .. import cfg_btn, mon_btn, pol_btn


details_page = Region(infoblock_type='detail')


def _db_select_query(name=None, type=None):
    """column order: `id`, `name`, `type`"""
    t_ems = cfmedb()['ext_management_systems']
    query = cfmedb().session.query(t_ems.id, t_ems.name, t_ems.type)
    if name:
        query = query.filter(t_ems.name == name)
    if type:
        query = query.filter(t_ems.type == type)
    return query


def _get_providers_page():
    sel.force_navigate('middleware_providers')

properties_form = Form(
    fields=[
        ('type_select', AngularSelect('emstype')),
        ('name_text', Input('name')),
        ('hostname_text', Input('default_hostname')),
        ('port_text', Input('default_api_port'))
    ])


@BaseProvider.add_base_type
class MiddlewareProvider(BaseProvider):
    in_version = ('5.7', version.LATEST)
    type_tclass = "middleware"
    page_name = 'middleware'
    string_name = 'Middleware'
    provider_types = {}
    STATS_TO_MATCH = []
    property_tuples = []
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add")
    save_button = form_buttons.FormButton("Save changes")
    taggable_type = 'ExtManagementSystem'


@navigator.register(MiddlewareProvider, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Middleware', 'Providers')(None)

    def resetter(self):
        # Reset view and selection
        tb.select("Grid View")
        sel.check(paginator.check_all())
        sel.uncheck(paginator.check_all())


@navigator.register(MiddlewareProvider, 'Add')
class Add(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a New Middleware Provider')


@navigator.register(MiddlewareProvider, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.click(Quadicon(self.obj.name, self.obj.quad_name))


@navigator.register(MiddlewareProvider, 'Edit')
class Edit(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        cfg_btn('Edit Selected Middleware Provider')


@navigator.register(MiddlewareProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Middleware Provider')


@navigator.register(MiddlewareProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        sel.check(Quadicon(self.obj.name, self.obj.quad_name).checkbox())
        pol_btn('Edit Tags')


@navigator.register(MiddlewareProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        pol_btn('Edit Tags')


@navigator.register(MiddlewareProvider, 'TimelinesFromDetails')
class TimelinesFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        mon_btn('Timelines')


@navigator.register(MiddlewareProvider, 'ProviderServers')
class ProviderServers(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Servers'))


@navigator.register(MiddlewareProvider, 'ProviderDatasources')
class ProviderDatasources(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Datasources'))


@navigator.register(MiddlewareProvider, 'ProviderDeployments')
class ProviderDeployments(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Deployments'))


@navigator.register(MiddlewareProvider, 'ProviderDomains')
class ProviderDomains(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Domains'))


@navigator.register(MiddlewareProvider, 'ProviderMessagings')
class ProviderMessagings(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock.element('Relationships', 'Middleware Messagings'))


@navigator.register(MiddlewareProvider, 'TopologyFromDetails')
class TopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        sel.click(InfoBlock('Overview', 'Topology'))

import_all_modules_of('cfme.middleware.provider')
