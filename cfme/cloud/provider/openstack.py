from mgmtsystem.openstack import OpenstackSystem
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider

from utils.version import current_version

from . import CloudProvider


@CloudProvider.add_provider_type
class OpenStackProvider(CloudProvider):
    type_name = "openstack"
    mgmt_class = OpenstackSystem

    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, sec_protocol=None, amqp_sec_protocol=None,
                 infra_provider=None):
        super(OpenStackProvider, self).__init__(name=name, credentials=credentials,
                                                zone=zone, key=key)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.infra_provider = infra_provider
        self.sec_protocol = sec_protocol
        self.amqp_sec_protocol = amqp_sec_protocol

    def create(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider is not None:
            if isinstance(self.infra_provider, OpenstackInfraProvider):
                infra_provider_name = self.infra_provider.name
            else:
                infra_provider_name = str(self.infra_provider)
            from utils.providers import setup_provider_by_name
            setup_provider_by_name(
                infra_provider_name, validate=True, check_existing=True)
        if current_version() >= "5.6" and 'validate_credentials' not in kwargs:
            # 5.6 requires validation, so unless we specify, we want to validate
            kwargs['validate_credentials'] = True
        return super(OpenStackProvider, self).create(*args, **kwargs)

    def _form_mapping(self, create=None, **kwargs):
        infra_provider = kwargs.get('infra_provider')
        if isinstance(infra_provider, OpenstackInfraProvider):
            infra_provider = infra_provider.name
        data_dict = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'OpenStack',
            'hostname_text': kwargs.get('hostname'),
            'api_port': kwargs.get('api_port'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol'),
            'infra_provider': "---" if infra_provider is False else infra_provider}
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
        creds = {'default': credentials}
        if 'amqp_credentials' in prov_config:
            amqp_credentials = cls.process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
            creds['amqp'] = amqp_credentials
        return cls(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port=prov_config['port'],
            credentials=creds,
            zone=prov_config['server_zone'],
            key=prov_key,
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            infra_provider=prov_config.get('infra_provider'))
