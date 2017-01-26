from utils.version import current_version
from mgmtsystem.openstack import OpenstackSystem

from . import CloudProvider


@CloudProvider.add_provider_type
class OpenStackProvider(CloudProvider):
    type_name = "openstack"
    mgmt_class = OpenstackSystem

    def __init__(self, name=None, credentials=None, zone=None, key=None, hostname=None,
                 ip_address=None, api_port=None, sec_protocol=None, amqp_sec_protocol=None,
                 tenant_mapping=None, infra_provider=None):
        super(OpenStackProvider, self).__init__(name=name, credentials=credentials,
                                                zone=zone, key=key)
        self.hostname = hostname
        self.ip_address = ip_address
        self.api_port = api_port
        self.infra_provider = infra_provider
        self.sec_protocol = sec_protocol
        self.tenant_mapping = tenant_mapping
        self.amqp_sec_protocol = amqp_sec_protocol

    def create(self, *args, **kwargs):
        # Override the standard behaviour to actually create the underlying infra first.
        if self.infra_provider:
            self.infra_provider.create(validate_credentials=True, validate_inventory=True,
                                       check_existing=True)
        if current_version() >= "5.6" and 'validate_credentials' not in kwargs:
            # 5.6 requires validation, so unless we specify, we want to validate
            kwargs['validate_credentials'] = True
        return super(OpenStackProvider, self).create(*args, **kwargs)

    def _form_mapping(self, create=None, **kwargs):
        infra_provider = kwargs.get('infra_provider')
        if infra_provider is None:
            # Don't look for the selectbox; it's either not there or we don't care what's selected
            infra_provider_name = None
        elif infra_provider is False:
            # Select nothing (i.e. deselect anything that is potentially currently selected)
            infra_provider_name = "---"
        else:
            infra_provider_name = infra_provider.name
        data_dict = {
            'name_text': kwargs.get('name'),
            'type_select': create and 'OpenStack',
            'hostname_text': kwargs.get('hostname'),
            'api_port': kwargs.get('api_port'),
            'ipaddress_text': kwargs.get('ip_address'),
            'sec_protocol': kwargs.get('sec_protocol'),
            'tenant_mapping': kwargs.get('tenant_mapping'),
            'infra_provider': infra_provider_name}
        if 'amqp' in self.credentials:
            data_dict.update({
                'event_selection': 'amqp',
                'amqp_hostname_text': kwargs.get('hostname'),
                'amqp_api_port': kwargs.get('amqp_api_port', '5672'),
                'amqp_sec_protocol': kwargs.get('amqp_sec_protocol', "Non-SSL")
            })
        return data_dict

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        if ('network_name' not in deploy_args) and self.data.get('network'):
            return {'network_name': self.data['network']}
        return {}

    @classmethod
    def from_config(cls, prov_config, prov_key):
        from utils.providers import get_crud
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        creds = {'default': credentials}
        if 'amqp_credentials' in prov_config:
            amqp_credentials = cls.process_credential_yaml_key(
                prov_config['amqp_credentials'], cred_type='amqp')
            creds['amqp'] = amqp_credentials
        infra_prov_key = prov_config.get('infra_provider_key')
        infra_provider = get_crud(infra_prov_key) if infra_prov_key else None
        return cls(name=prov_config['name'],
            hostname=prov_config['hostname'],
            ip_address=prov_config['ipaddress'],
            api_port=prov_config['port'],
            credentials=creds,
            zone=prov_config['server_zone'],
            key=prov_key,
            sec_protocol=prov_config.get('sec_protocol', "Non-SSL"),
            tenant_mapping=prov_config.get('tenant_mapping', False),
            infra_provider=infra_provider)
