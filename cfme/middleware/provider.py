from cfme.common.provider import BaseProvider
from cfme.web_ui import (
    Form, AngularSelect, form_buttons, Input
)
from cfme.web_ui.menu import nav

from . import cfg_btn, mon_btn, pol_btn, list_tbl

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
    page_name = 'middleware'
    string_name = 'Middleware'
    provider_suffix = 'Manager'
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Middleware Manager")
    save_button = form_buttons.FormButton("Save Changes")

    def __init__(self, name=None, hostname=None, port=None, credentials=None, key=None):
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
