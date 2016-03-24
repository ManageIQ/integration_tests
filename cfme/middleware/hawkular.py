from cfme.common.provider import BaseProvider
from cfme.web_ui import (
    Form, AngularSelect, form_buttons, Input
)
from cfme.web_ui.menu import nav


from . import cfg_btn

nav.add_branch(
    'middleware_providers',
    {
        'middleware_provider_new':
            lambda _: cfg_btn('Add a New Middleware Provider')
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
    page_name = "middleware"
    properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Middleware Manager")

    def __init__(self, name=None, hostname=None, port=None, credentials=None):
        self.name = name
        self.hostname = hostname
        self.port = port
        if not credentials:
            credentials = {}
        self.credentials = credentials

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Hawkular',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port')}
