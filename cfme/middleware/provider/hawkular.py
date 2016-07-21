import re

from utils.varmeth import variable

from cfme.common.provider import BaseProvider
from . import properties_form, _get_providers_page, _db_select_query
from .. import download, MiddlewareBase
from mgmtsystem.hawkular import Hawkular
from cfme.web_ui import form_buttons
from utils.db import cfmedb


@BaseProvider.add_type_map
class HawkularProvider(MiddlewareBase, BaseProvider):
    """
    HawkularProvider class holds provider data. Used to perform actions on hawkular provider page

    Args:
        name: Name of the provider
        hostname: Hostname/IP of the provider
        port: http/https port of hawkular provider
        credentials: see Credential inner class.
        key: The CFME key of the provider in the yaml.
        db_id: database row id of provider

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
    type_tclass = "middleware"
    type_name = "hawkular"
    mgmt_class = Hawkular
    page_name = 'middleware'
    string_name = 'Middleware'
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    _properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Middleware Provider")
    save_button = form_buttons.FormButton("Save Changes")
    taggable_type = 'ExtManagementSystem'

    def __init__(self, name=None, hostname=None, port=None, credentials=None, key=None, **kwargs):
        self.name = name
        self.hostname = hostname
        self.port = port
        self.provider_type = 'Hawkular'
        if not credentials:
            credentials = {}
        self.credentials = credentials
        self.key = key
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None

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

    @variable(alias='ui')
    def is_refreshed(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        if re.match('Success.*Minute.*Ago', self.summary.status.last_refresh.text_value):
            return True
        else:
            return False

    @is_refreshed.variant('db')
    def is_refreshed_db(self):
        ems = cfmedb()['ext_management_systems']
        dates = cfmedb().session.query(ems.created_on,
                                       ems.updated_on).filter(ems.name == self.name).first()
        return dates.updated_on > dates.created_on

    @classmethod
    def download(cls, extension):
        _get_providers_page()
        download(extension)

    def load_details(self, refresh=False):
        """Call super class `load_details` and load `db_id` if not set"""
        BaseProvider.load_details(self, refresh=refresh)
        if not self.db_id or refresh:
            tmp_provider = _db_select_query(
                name=self.name, type='ManageIQ::Providers::Hawkular::MiddlewareManager').first()
            self.db_id = tmp_provider.id

    @staticmethod
    def configloader(prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = HawkularProvider.process_credential_yaml_key(credentials_key)
        return HawkularProvider(
            name=prov_config['name'],
            key=prov_key,
            hostname=prov_config['hostname'],
            port=prov_config['port'],
            credentials={'default': credentials})
