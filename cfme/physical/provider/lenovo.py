from widgetastic_patternfly import Input
from wrapanapi.lenovo import LenovoSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from . import PhysicalProvider


class LenovoEndpoint(DefaultEndpoint):
    api_port = 443

    @property
    def view_value_mapping(self):
        return {
            'hostname': self.hostname,
            'api_port': self.api_port
        }


class LenovoEndpointForm(DefaultEndpointForm):
    api_port = Input('default_api_port')


class LenovoProvider(PhysicalProvider):
    type_name = 'lenovo'
    endpoints_form = LenovoEndpointForm
    string_name = 'Physical Infrastructure'
    mgmt_class = LenovoSystem
    refresh_text = "Refresh Relationships and Power States"
    db_types = ["Lenovo::PhysicalInfraManager"]
    settings_key = 'ems_lenovo'

    def __init__(self, appliance, name=None, key=None, endpoints=None):
        super(LenovoProvider, self).__init__(
            appliance=appliance, name=name, key=key, endpoints=endpoints
        )

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = LenovoEndpoint(**prov_config['endpoints']['default'])
        return cls(name=prov_config['name'],
                   endpoints={endpoint.name: endpoint},
                   key=prov_key,
                   appliance=appliance)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Lenovo XClarity'
        }
