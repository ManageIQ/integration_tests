from . import ContainersProvider
from wrapanapi.containers.providers.kubernetes import Kubernetes


class KubernetesProvider(ContainersProvider):
    type_name = "kubernetes"
    mgmt_class = Kubernetes
    db_types = ["Kubernetes::ContainerManager"]

    def _form_mapping(self, create=None, **kwargs):
        if self.appliance.version > '5.8.0.3':
            sec_protocol = kwargs.get('sec_protocol')
        else:
            sec_protocol = None
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Kubernetes',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'sec_protocol': sec_protocol,
                'zone_select': kwargs.get('zone'),
                'hawkular_hostname': kwargs.get('hawkular_hostname'),
                'hawkular_sec_protocol': kwargs.get('hawkular_sec_protocol')}

    @staticmethod
    def from_config(prov_config, prov_key, appliance=None):
        token_creds = KubernetesProvider.process_credential_yaml_key(
            prov_config['credentials'], cred_type='token')
        return KubernetesProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=prov_key,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname') or prov_config['ip_address'],
            port=prov_config['port'],
            sec_protocol=prov_config.get('sec_protocol'),
            hawkular_hostname=prov_config.get('hawkular_hostname'),
            hawkular_port=prov_config.get('hawkular_port'),
            hawkular_sec_protocol=prov_config.get('hawkular_sec_protocol'),
            provider_data=prov_config,
            appliance=appliance)
