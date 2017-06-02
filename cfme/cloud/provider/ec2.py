from . import CloudProvider
import cfme.fixtures.pytest_selenium as sel
from mgmtsystem.ec2 import EC2System


class EC2Provider(CloudProvider):
    type_name = "ec2"
    mgmt_class = EC2System
    db_types = ["Amazon::CloudManager"]

    def __init__(
            self, name=None, credentials=None, zone=None, key=None, region=None, appliance=None):
        super(EC2Provider, self).__init__(name=name, credentials=credentials,
                                          zone=zone, key=key, appliance=appliance)
        self.region = region

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Amazon EC2',
                'region_select': sel.ByValue(kwargs.get('region'))}

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        return cls(name=prov_config['name'],
            region=prov_config['region'],
            credentials={'default': credentials},
            zone=prov_config['server_zone'],
            key=prov_key,
            appliance=appliance)
