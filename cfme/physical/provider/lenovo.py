from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from wrapanapi.lenovo import LenovoSystem

from . import PhysicalProvider


class LenovoEndpoint(DefaultEndpoint):
    pass


class LenovoEndpointForm(DefaultEndpointForm):
    pass


class LenovoProvider(PhysicalProvider):
    type_name = 'lenovo'
    endpoints_form = LenovoEndpointForm
    string_name = "Ems Physical Infras"

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
        return {'name': self.name,
                'prov_type': 'Lenovo XClarity'
                }
