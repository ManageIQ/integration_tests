from . import InfraProvider, prop_region
from mgmtsystem.openstack_infra import OpenstackInfraSystem


@InfraProvider.add_provider_type
class OpenstackInfraProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_host']
    _properties_region = prop_region
    type_name = "openstack-infra"
    mgmt_class = OpenstackInfraSystem

    def __init__(self, name=None, credentials=None, key=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None,
                 sec_protocol=None):
        super(OpenstackInfraProvider, self).__init__(name=name, credentials=credentials,
                                             key=key, provider_data=provider_data)

        self.hostname = hostname
        self.ip_address = ip_address
        self.start_ip = start_ip
        self.end_ip = end_ip
        self.sec_protocol = sec_protocol

    def _form_mapping(self, create=None, **kwargs):
        data_dict = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'OpenStack Platform Director',
            'hostname_text': kwargs.get('hostname'),
            'api_port': kwargs.get('api_port'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol'),
            'amqp_sec_protocol': kwargs.get('amqp_sec_protocol')}
        if 'amqp' in self.credentials:
            data_dict.update({
                'event_selection': 'amqp',
                'amqp_hostname_text': kwargs.get('hostname'),
                'amqp_api_port': kwargs.get('amqp_api_port', '5672'),
                'amqp_sec_protocol': kwargs.get('amqp_sec_protocol', "Non-SSL")
            })
        return data_dict

    @classmethod
    def from_config(cls, prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        credential_dict = {'default': credentials}
        if prov_config.get('discovery_range', None):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        if 'ssh_credentials' in prov_config:
            credential_dict['ssh'] = OpenstackInfraProvider.process_credential_yaml_key(
                prov_config['ssh_credentials'], cred_type='ssh')
        if 'amqp_credentials' in prov_config:
            credential_dict['amqp'] = OpenstackInfraProvider.process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
        return cls(
            name=prov_config['name'],
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            credentials=credential_dict,
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)
