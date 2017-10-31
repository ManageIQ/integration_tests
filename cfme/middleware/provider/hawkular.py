import re

from widgetastic_patternfly import Input, BootstrapSelect
from wrapanapi.hawkular import Hawkular

from cfme.common import TopologyMixin, TimelinesMixin
from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.varmeth import variable

from . import MiddlewareProvider
from . import _get_providers_page, _db_select_query
from . import download, MiddlewareBase


class HawkularEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'security_protocol': self.security_protocol,
                'hostname': self.hostname,
                'api_port': self.api_port,
                }


class HawkularEndpointForm(DefaultEndpointForm):
    security_protocol = BootstrapSelect('default_security_protocol')
    api_port = Input('default_api_port')


class HawkularProvider(MiddlewareBase, TopologyMixin, TimelinesMixin, MiddlewareProvider):
    """
    HawkularProvider class holds provider data. Used to perform actions on hawkular provider page

    Args:
        name: Name of the provider
        endpoints: one or several provider endpoints like DefaultEndpoint. it should be either dict
        in format dict{endpoint.name, endpoint, endpoint_n.name, endpoint_n}, list of endpoints or
        mere one endpoint
        hostname: Hostname/IP of the provider
        port: http/https port of hawkular provider
        credentials: see Credential inner class.
        key: The CFME key of the provider in the yaml.
        db_id: database row id of provider

    Usage:

        myprov = HawkularProvider(name='foo',
                            endpoints=endpoint,
                            hostname='localhost',
                            port=8080,
                            credentials=Provider.Credential(principal='admin', secret='foobar')))
        myprov.create()
        myprov.num_deployment(method="ui")
    """
    STATS_TO_MATCH = MiddlewareProvider.STATS_TO_MATCH +\
        ['num_server', 'num_domain', 'num_deployment', 'num_datasource', 'num_messaging']
    property_tuples = MiddlewareProvider.property_tuples +\
        [('name', 'Name'), ('hostname', 'Host Name'), ('port', 'Port'), ('provider_type', 'Type')]
    type_name = "hawkular"
    mgmt_class = Hawkular
    db_types = ["Hawkular::MiddlewareManager"]
    endpoints_form = HawkularEndpointForm

    def __init__(self, name=None, endpoints=None, hostname=None, port=None,
                 credentials=None, key=None,
                 appliance=None, sec_protocol=None, **kwargs):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.hostname = hostname
        self.port = port
        self.provider_type = 'Hawkular'
        if not credentials:
            credentials = {}
        self.credentials = credentials
        self.key = key
        self.sec_protocol = sec_protocol if sec_protocol else 'Non-SSL'
        self.db_id = kwargs['db_id'] if 'db_id' in kwargs else None
        self.endpoints = self._prepare_endpoints(endpoints)

    @property
    def view_value_mapping(self):
        """Maps values to view attrs"""
        return {
            'name': self.name,
            'prov_type': 'Hawkular'
        }

    @variable(alias='db')
    def num_deployment(self):
        return self._num_db_generic('middleware_deployments')

    @num_deployment.variant('ui')
    def num_deployment_ui(self, reload_data=True):
        self.load_details(refresh=reload_data)
        return int(self.get_detail("Relationships", "Middleware Deployments"))

    @variable(alias='db')
    def num_server(self):
        return self._num_db_generic('middleware_servers')

    @num_server.variant('ui')
    def num_server_ui(self, reload_data=True):
        self.load_details(refresh=reload_data)
        return int(self.get_detail("Relationships", "Middleware Servers"))

    @variable(alias='db')
    def num_server_group(self):
        res = self.appliance.db.client.engine.execute(
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
        self.load_details(refresh=reload_data)
        return int(self.get_detail("Relationships", "Middleware Datasources"))

    @variable(alias='db')
    def num_domain(self):
        return self._num_db_generic('middleware_domains')

    @num_domain.variant('ui')
    def num_domain_ui(self, reload_data=True):
        self.load_details(refresh=reload_data)
        return int(self.get_detail("Relationships", "Middleware Domains"))

    @variable(alias='db')
    def num_messaging(self):
        return self._num_db_generic('middleware_messagings')

    @num_messaging.variant('ui')
    def num_messaging_ui(self, reload_data=True):
        self.load_details(refresh=reload_data)
        return int(self.get_detail("Relationships", "Middleware Messagings"))

    @variable(alias='ui')
    def is_refreshed(self, reload_data=True):
        self.load_details(refresh=reload_data)
        if re.match('Success.*Minute.*Ago', self.get_detail("Status", "Last Refresh")):
            return True
        else:
            return False

    @is_refreshed.variant('db')
    def is_refreshed_db(self):
        ems = self.appliance.db.client['ext_management_systems']
        dates = self.appliance.db.client.session.query(ems.created_on,
                                       ems.updated_on).filter(ems.name == self.name).first()
        return dates.updated_on > dates.created_on

    @variable(alias='ui')
    def is_valid(self, reload_data=True):
        self.load_details(refresh=reload_data)
        if re.match('Valid.*Ok', self.get_detail("Status", "Authentication status")):
            return True
        else:
            return False

    @classmethod
    def download(cls, extension):
        view = _get_providers_page()
        download(view, extension)

    def load_details(self, refresh=False):
        """Navigate to Details and load `db_id` if not set"""
        view = navigate_to(self, 'Details')
        if not self.db_id or refresh:
            tmp_provider = _db_select_query(
                name=self.name, type='ManageIQ::Providers::Hawkular::MiddlewareManager').first()
            self.db_id = tmp_provider.id
        if refresh:
            view.browser.selenium.refresh()
            view.flush_widget_cache()
        return view

    def load_topology_page(self):
        return navigate_to(self, 'TopologyFromDetails')

    def recheck_auth_status(self):
        view = self.load_details(refresh=True)
        view.toolbar.authentication.item_select("Re-check Authentication Status")

    def load_timelines_page(self):
        view = self.load_details()
        view.toolbar.monitoring.item_select("Timelines")

    @staticmethod
    def from_config(prov_config, prov_key, appliance=None):
        credentials_key = prov_config['credentials']
        credentials = HawkularProvider.process_credential_yaml_key(credentials_key)
        endpoints = {}
        endpoints[HawkularEndpoint.name] = HawkularEndpoint(
            **prov_config['endpoints'][HawkularEndpoint.name])
        return HawkularProvider(
            name=prov_config['name'],
            endpoints=endpoints,
            key=prov_key,
            hostname=prov_config['hostname'],
            sec_protocol=prov_config.get('sec_protocol'),
            port=prov_config['port'],
            credentials={'default': credentials},
            appliance=appliance)
