from . import InfraProvider
from mgmtsystem.virtualcenter import VMWareSystem


@InfraProvider.add_provider_type
class VMwareProvider(InfraProvider):
    type_name = "virtualcenter"
    mgmt_class = VMWareSystem

    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None):
        super(VMwareProvider, self).__init__(name=name, credentials=credentials,
                                             zone=zone, key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'VMware vCenter',
                'hostname_text': kwargs.get('hostname'),
                'ipaddress_text': kwargs.get('ip_address')}

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        if "allowed_datastores" not in deploy_args and "allowed_datastores" in self.data:
            return {'allowed_datastores': self.data['allowed_datastores']}
        return {}

    @classmethod
    def from_config(cls, prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials={'default': credentials},
            zone=prov_config['server_zone'],
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)
