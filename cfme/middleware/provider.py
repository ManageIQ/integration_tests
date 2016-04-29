from cfme.common.provider import BaseProvider
from cfme.web_ui import (
    Form, AngularSelect, form_buttons, Input
)
from cfme.web_ui.menu import nav

from . import cfg_btn, mon_btn, pol_btn, list_tbl
from utils.varmeth import variable
from cfme.fixtures import pytest_selenium as sel

nav.add_branch(
    'middleware_providers',
    {
        'middleware_provider_new':
            lambda _: cfg_btn('Add a New Middleware Provider'),
        'middleware_provider':
        [
            lambda ctx: list_tbl.select_row('name', ctx['provider'].name),
            {
                'middleware_provider_edit':
                lambda _: cfg_btn('Edit Selected Middleware Provider'),
                'middleware_provider_edit_tags':
                lambda _: pol_btn('Edit Tags')
            }],
        'middleware_provider_detail':
        [
            lambda ctx: list_tbl.click_cells({'name': ctx['provider'].name}),
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


class HawkularProvider(BaseProvider):
    STATS_TO_MATCH = ['num_server', 'num_deployment']

    page_name = 'middleware'
    string_name = 'Middleware'
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton(
        "Add this Middleware Provider")
    save_button = form_buttons.FormButton("Save Changes")

    def __init__(self, name=None, hostname=None,
                 port=None, credentials=None, key=None):
        self.name = name
        self.hostname = hostname
        self.port = port
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
    def num_deployment_ui(self):
        return int(self.get_detail("Relationships", "Middleware Deployments"))

    @variable(alias='db')
    def num_server(self):
        return self._num_db_generic('middleware_servers')

    @num_server.variant('ui')
    def num_server_ui(self):
        return int(self.get_detail("Relationships", "Middleware Servers"))

    def nav_to_provider_view(self):
        sel.force_navigate('middleware_providers', context={
            'provider': self})

    def nav_to_provider_detailed_view(self):
        if not self._on_detail_page():
            self.load_details()
#            sel.force_navigate('middleware_provider_detail', context={
#               'provider': self})

    def _on_detail_page(self):
        sel.ensure_browser_open()
        return sel.is_displayed_text("{} (Summary)".format(self.name))
