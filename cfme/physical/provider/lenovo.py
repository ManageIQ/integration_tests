from . import PhysicalProvider


class LenovoProvider(PhysicalProvider):
    def __init__(self, appliance, name):
        super(LenovoProvider, self).__init__(appliance, name)

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        # Will need an endpoint created
        # endpoint = VirtualCenterEndpoint(**prov_config['endpoints']['default'])

        return cls(name=prov_config['name'],
                   appliance=appliance)
