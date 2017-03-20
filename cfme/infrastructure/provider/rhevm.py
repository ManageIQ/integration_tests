from utils import version
from . import InfraProvider, prop_region
from mgmtsystem.rhevm import RHEVMSystem


class RHEVMProvider(InfraProvider):
    _properties_region = prop_region
    type_name = "rhevm"
    mgmt_class = RHEVMSystem
    db_types = ["Redhat::InfraManager"]

    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, verify_tls=False, ca_certs=None, start_ip=None,
                 end_ip=None,
                 provider_data=None, appliance=None):
        super(RHEVMProvider, self).__init__(
            name=name, credentials=credentials, zone=zone, key=key, provider_data=provider_data,
            appliance=appliance)

        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.verify_tls = verify_tls
        self.ca_certs = ca_certs
        self.start_ip = start_ip
        self.end_ip = end_ip

    def _form_mapping(self, create=None, **kwargs):
        provider_name = version.pick({
            version.LOWEST: 'Red Hat Enterprise Virtualization Manager',
            '5.7.1': 'Red Hat Virtualization Manager'})
        verify_tls = version.pick({
            version.LOWEST: None,
            '5.8': kwargs.get('verify_tls', False)})
        ca_certs = version.pick({
            version.LOWEST: None,
            '5.8': kwargs.get('ca_certs', None)})

        main_values = {
            'name': kwargs.get('name'),
            'prov_type': create and provider_name,
            'verify_tls_switch': verify_tls,
            'ca_certs': ca_certs
        }

        endpoint_values = {
            'default': {
                'hostname': kwargs.get('hostname'),
                'api_port': kwargs.get('api_port'),
                # 'ipaddress_text': kwargs.get('ip_address'),
                },
            'database': {
                'hostname': kwargs.get('hostname') if self.credentials.get('candu', None) else None
            }
        }
        return main_values, endpoint_values

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        if 'default_cluster' not in deploy_args:
            return {'cluster': self.data['default_cluster']}
        return {}

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        credentials_key = prov_config['credentials']
        credentials = {
            # The default credentials for controlling the provider
            'default': cls.process_credential_yaml_key(credentials_key),
        }
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        if prov_config.get('candu_credentials', None):
            # Insert C&U credentials if those are present
            credentials['candu'] = RHEVMProvider.process_credential_yaml_key(
                prov_config['candu_credentials'], cred_type='candu')
        return cls(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port='',
            credentials=credentials,
            zone=prov_config.get('server_zone', 'default'),
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip,
            appliance=appliance)
