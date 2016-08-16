from __future__ import unicode_literals
from . import Provider
from utils.varmeth import variable
from mgmtsystem.openshift import Openshift


@Provider.add_type_map
class OpenshiftProvider(Provider):
    STATS_TO_MATCH = Provider.STATS_TO_MATCH + ['num_route']
    type_name = "openshift"
    mgmt_class = Openshift

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        super(OpenshiftProvider, self).__init__(
            name=name, credentials=credentials, key=key, zone=zone, hostname=hostname, port=port,
            provider_data=provider_data)

    def create(self, validate_credentials=True, **kwargs):
        # Workaround - randomly fails on 5.5.0.8 with no validation
        # probably a js wait issue, not reproducible manually
        super(OpenshiftProvider, self).create(validate_credentials=validate_credentials, **kwargs)

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenShift',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'zone_select': kwargs.get('zone')}

    @variable(alias='db')
    def num_route(self):
        return self._num_db_generic('container_routes')

    @num_route.variant('ui')
    def num_route_ui(self):
        return int(self.get_detail("Relationships", "Routes"))

    @staticmethod
    def configloader(prov_config, prov_key):
        token_creds = OpenshiftProvider.process_credential_yaml_key(
            prov_config['credentials'], cred_type='token')
        return OpenshiftProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=prov_key,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
