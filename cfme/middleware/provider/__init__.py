from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Form, AngularSelect, Input, Quadicon, form_buttons
)
from cfme.web_ui.menu import nav
from cfme.common.provider import BaseProvider
from utils import version
from utils.db import cfmedb
from cfme.common.provider import import_all_modules_of
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

nav.add_branch(
    'middleware_providers',
    {
        'middleware_provider_new':
            lambda _: cfg_btn('Add a New Middleware Provider'),
        'middleware_provider':
        [
            lambda ctx: sel.check(Quadicon(ctx['provider'].name, "middleware").checkbox),
            {
                'middleware_provider_edit':
                lambda _: cfg_btn('Edit Selected Middleware Provider'),
                'middleware_provider_edit_tags':
                lambda _: pol_btn('Edit Tags')
            }],
        'middleware_provider_detail':
        [
            lambda ctx: sel.click(Quadicon(ctx['provider'].name, "middleware")),
            {
                'middleware_provider_edit_detail':
                lambda _: cfg_btn('Edit this Middleware Provider'),
                'middleware_provider_timelines_detail':
                lambda _: mon_btn('Timelines'),
                'middleware_provider_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
            }]
    }
)

properties_form = Form(
    fields=[
        ('type_select', AngularSelect('server_emstype')),
        ('name_text', Input('name')),
        ('hostname_text', Input('hostname')),
        ('port_text', Input('port'))
    ])


@BaseProvider.add_base_type
class MiddlewareProvider(BaseProvider):
    in_version = ('5.7', version.LATEST)
    type_tclass = "middleware"
    page_name = 'middleware'
    string_name = 'Middleware'
    provider_types = {}
    STATS_TO_MATCH = ['num_server', 'num_deployment', 'num_datasource']
    property_tuples = [('name', 'name'), ('hostname', 'host_name'), ('port', 'port'),
                       ('provider_type', 'type')]
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Middleware Provider")
    save_button = form_buttons.FormButton("Save Changes")
    taggable_type = 'ExtManagementSystem'


import_all_modules_of('cfme.middleware.provider')
