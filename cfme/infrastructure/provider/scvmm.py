from mgmtsystem.scvmm import SCVMMSystem
from . import Provider


@Provider.add_type_map
class SCVMMProvider(Provider):
    STATS_TO_MATCH = ['num_template', 'num_vm']
    type_name = "scvmm"
    mgmt_system = SCVMMSystem

    def __init__(self, name=None, credentials=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, sec_protocol=None, sec_realm=None,
                 provider_data=None):
        super(SCVMMProvider, self).__init__(name=name, credentials=credentials,
            zone=zone, key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol
        self.sec_realm = sec_realm

    def _form_mapping(self, create=None, **kwargs):

        values = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'Microsoft System Center VMM',
            'hostname_text': kwargs.get('hostname'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol')
        }

        if 'sec_protocol' in values and values['sec_protocol'] is 'Kerberos':
            values['sec_realm'] = kwargs.get('sec_realm')

        return values

    @classmethod
    def configloader(cls, prov_config, prov_key):
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
            sec_realm=prov_config['sec_realm'])
