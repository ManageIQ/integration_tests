from . import ContainersProvider
from mgmtsystem.kubernetes import Kubernetes


@ContainersProvider.add_provider_type
class KubernetesProvider(ContainersProvider):
    type_name = "kubernetes"
    mgmt_class = Kubernetes

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        super(KubernetesProvider, self).__init__(
            name=name, credentials=credentials, key=key, zone=zone, hostname=hostname, port=port,
            provider_data=provider_data)

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Kubernetes',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'zone_select': kwargs.get('zone')}

    @staticmethod
    def from_config(prov_config, prov_key):
        token_creds = KubernetesProvider.process_credential_yaml_key(
            prov_config['credentials'], cred_type='token')
        return KubernetesProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=prov_key,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)
