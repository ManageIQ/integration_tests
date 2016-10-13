import re

from cfme.common import TopologyMixin, TimelinesMixin
from . import MiddlewareProvider
from mgmtsystem.hawkular import Hawkular
from utils.appliance import Navigatable
from utils.db import cfmedb
from utils.varmeth import variable
from . import _get_providers_page, _db_select_query
from .. import download, MiddlewareBase, auth_btn, mon_btn


@MiddlewareProvider.add_provider_type
class HawkularProvider(MiddlewareBase, TopologyMixin, TimelinesMixin, MiddlewareProvider):
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
    STATS_TO_MATCH = MiddlewareProvider.STATS_TO_MATCH +\
        ['num_server', 'num_domain', 'num_deployment', 'num_datasource', 'num_messaging']
    property_tuples = MiddlewareProvider.property_tuples +\
        [('name', 'name'), ('hostname', 'host_name'), ('port', 'port'), ('provider_type', 'type')]
    type_name = "hawkular"
    mgmt_class = Hawkular

    def __init__(self, name=None, hostname=None, port=None, credentials=None, key=None,
            appliance=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
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
    def num_server_group(self):
        res = cfmedb().engine.execute(
            "SELECT count(*) "
            "FROM ext_management_systems, middleware_domains, middleware_server_groups "
            "WHERE middleware_domains.ems_id=ext_management_systems.id "
            "AND middleware_domains.id=middleware_server_groups.domain_id "
            "AND ext_management_systems.name='{0}'".format(self.name))
        return int(res.first()[0])

    @variable(alias='db')
    def num_datasource(self):
        return self._num_db_generic('middleware_datasources')

    @num_datasource.variant('ui')
    def num_datasource_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_datasources.value

    @variable(alias='db')
    def num_domain(self):
        return self._num_db_generic('middleware_domains')

    @num_domain.variant('ui')
    def num_domain_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_domains.value

    @variable(alias='db')
    def num_messaging(self):
        return self._num_db_generic('middleware_messagings')

    @num_messaging.variant('ui')
    def num_messaging_ui(self, reload_data=True):
        if reload_data:
            self.summary.reload()
        return self.summary.relationships.middleware_messagings.value

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
        MiddlewareProvider.load_details(self, refresh=refresh)
        if not self.db_id or refresh:
            tmp_provider = _db_select_query(
                name=self.name, type='ManageIQ::Providers::Hawkular::MiddlewareManager').first()
            self.db_id = tmp_provider.id

    def load_topology_page(self):
        self.summary.reload()
        self.summary.overview.topology.click()

    def recheck_auth_status(self):
        self.load_details(refresh=True)
        auth_btn("Re-check Authentication Status")

    def load_timelines_page(self):
        self.load_details()
        mon_btn("Timelines")

    @staticmethod
    def from_config(prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = HawkularProvider.process_credential_yaml_key(credentials_key)
        return HawkularProvider(
            name=prov_config['name'],
            key=prov_key,
            hostname=prov_config['hostname'],
            port=prov_config['port'],
            credentials={'default': credentials})
