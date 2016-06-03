from cfme.common.provider import BaseProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Form, AngularSelect, form_buttons, Input, Quadicon
)
from cfme.web_ui.menu import nav
from utils.varmeth import variable
from . import cfg_btn, mon_btn, pol_btn, MiddlewareBase

details_page = Region(infoblock_type='detail')

nav.add_branch(
    'middleware_providers',
    {
        'middleware_provider_new':
            lambda _: cfg_btn('Add a New Middleware Provider'),
        'middleware_provider':
        [
            lambda ctx: sel.check(Quadicon(ctx['provider'].name).checkbox),
            {
                'middleware_provider_edit':
                lambda _: cfg_btn('Edit Selected Middleware Provider'),
                'middleware_provider_edit_tags':
                lambda _: pol_btn('Edit Tags')
            }],
        'middleware_provider_detail':
        [
            lambda ctx: sel.click(Quadicon(ctx['provider'].name)),
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


class HawkularProvider(MiddlewareBase, BaseProvider):
    """
    HawkularProvider class holds provider data. Used to perform actions on hawkular provider page

    Args:
        name: Name of the provider
        hostname: Hostname/IP of the provider
        port: http/https port of hawkular provider
        credentials: see Credential inner class.
        key: The CFME key of the provider in the yaml.

    Usage:

        myprov = HawkularProvider(name='foo',
                            hostname='localhost',
                            port=8080,
                            credentials=Provider.Credential(principal='admin', secret='foobar')))
        myprov.create()
        myprov.num_deployment(method="ui")
    """
    STATS_TO_MATCH = ['num_server', 'num_deployment', 'num_datasource']
    property_tuples = [('name', 'name'), ('hostname', 'host_name'), ('port', 'port'),
                       ('provider_type', 'type')]

    page_name = 'middleware'
    string_name = 'Middleware'
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Middleware Provider")
    save_button = form_buttons.FormButton("Save Changes")

    def __init__(self, name=None, hostname=None, port=None, credentials=None, key=None):
        self.name = name
        self.hostname = hostname
        self.port = port
        self.provider_type = 'Hawkular'
        if not credentials:
            credentials = {}
        self.credentials = credentials
        self.key = key

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Hawkular',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port')}

    @variable(alias='db')
    def num_deployment(self):
        return self._num_db_generic('middleware_deployments')

    @num_deployment.variant('ui')
    def num_deployment_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_deployments.value

    @variable(alias='db')
    def num_server(self):
        return self._num_db_generic('middleware_servers')

    @num_server.variant('ui')
    def num_server_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_servers.value

    @variable(alias='db')
    def num_datasource(self):
        return self._num_db_generic('middleware_datasources')

    @num_datasource.variant('ui')
    def num_datasource_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_datasources.value
