from wrapanapi.ec2 import EC2System

from . import CloudProvider
from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm


class EC2Endpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {}


class EC2EndpointForm(DefaultEndpointForm):
    pass


class EC2Provider(CloudProvider):
    type_name = "ec2"
    mgmt_class = EC2System
    db_types = ["Amazon::CloudManager"]
    endpoints_form = EC2EndpointForm

    def __init__(
            self, name=None, endpoints=None, zone=None, key=None, region=None, appliance=None):
        super(EC2Provider, self).__init__(name=name, endpoints=endpoints,
                                          zone=zone, key=key, appliance=appliance)
        self.region = region

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Amazon EC2',
            'region': self.region,
        }

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = EC2Endpoint(**prov_config['endpoints']['default'])
        return cls(name=prov_config['name'],
            region=prov_config['region'],
            endpoints={endpoint.name: endpoint},
            zone=prov_config['server_zone'],
            key=prov_key,
            appliance=appliance)
