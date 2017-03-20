from . import InfraProvider
from mgmtsystem.scvmm import SCVMMSystem


class SCVMMProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_vm']
    type_name = "scvmm"
    mgmt_class = SCVMMSystem
    db_types = ["Microsoft::InfraManager"]

    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, sec_protocol=None, sec_realm=None,
                 provider_data=None, appliance=None):
        super(SCVMMProvider, self).__init__(
            name=name, credentials=credentials, zone=zone, key=key, provider_data=provider_data,
            appliance=appliance)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol
        self.sec_realm = sec_realm

    def _form_mapping(self, create=None, **kwargs):

        main_values = {
            'name': kwargs.get('name'),
            'prov_type': create and 'Microsoft System Center VMM',
        }

        endpoint_values = {
            'default': {
                'hostname': kwargs.get('hostname'),
                # 'ipaddress_text': kwargs.get('ip_address'),
                'security_protocol': kwargs.get('sec_protocol')
            }
        }

        if 'security_protocol' in endpoint_values['default'] and \
                        endpoint_values['default']['security_protocol'] is 'Kerberos':
            endpoint_values['realm'] = kwargs.get('sec_realm')

        return main_values, endpoint_values

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        values = {}
        if 'host_group' not in deploy_args:
            values['host_group'] = self.data.get("host_group", "All Hosts")
        if 'cpu' not in deploy_args:
            values['cpu'] = self.data.get("cpu", 0)
        if 'ram' not in deploy_args:
            values['ram'] = self.data.get("ram", 0)
        return values

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(
            name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials={'default': credentials},
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip,
            sec_protocol=prov_config['sec_protocol'],
            sec_realm=prov_config['sec_realm'],
            appliance=appliance)
