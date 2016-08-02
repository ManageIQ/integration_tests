from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Form, AngularSelect, Input, Quadicon
)
from cfme.web_ui.menu import nav
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

import_all_modules_of('cfme.middleware.provider')
