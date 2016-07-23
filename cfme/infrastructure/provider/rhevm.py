from mgmtsystem.rhevm import RHEVMSystem
from . import Provider, prop_region


@Provider.add_type_map
class RHEVMProvider(Provider):
    _properties_region = prop_region
    type_name = "rhevm"
    mgmt_class = RHEVMSystem

    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, start_ip=None, end_ip=None,
                 provider_data=None):
        super(RHEVMProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.start_ip = start_ip
        self.end_ip = end_ip

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Red Hat Enterprise Virtualization Manager',
                'hostname_text': kwargs.get('hostname'),
                'api_port': kwargs.get('api_port'),
                'ipaddress_text': kwargs.get('ip_address'),
                'candu_hostname_text':
                kwargs.get('hostname') if self.credentials.get('candu', None) else None}

    @classmethod
    def configloader(cls, prov_config, prov_key):
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
            zone=prov_config['server_zone'],
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)
