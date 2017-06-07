from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from . import InfraProvider
from mgmtsystem.virtualcenter import VMWareSystem


class VirtualCenterEndpoint(DefaultEndpoint):
    pass


class VirtualCenterEndpointForm(DefaultEndpointForm):
    pass


class VMwareProvider(InfraProvider):
    type_name = "virtualcenter"
    mgmt_class = VMWareSystem
    db_types = ["Vmware::InfraManager"]
    endpoints_form = VirtualCenterEndpointForm

    def __init__(self, name=None, endpoints=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None, appliance=None):
        super(VMwareProvider, self).__init__(
            name=name, endpoints=endpoints, zone=zone, key=key, provider_data=provider_data,
            appliance=appliance)
        self.hostname = hostname
        self.start_ip = start_ip
        self.end_ip = end_ip
        if ip_address:
            self.ip_address = ip_address

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        # Called within a dictionary update. Since we want to remove key/value pairs, return the
        # entire dictionary
        deploy_args.pop('username', None)
        deploy_args.pop('password', None)
        if "allowed_datastores" not in deploy_args and "allowed_datastores" in self.data:
            deploy_args['allowed_datastores'] = self.data['allowed_datastores']

        return deploy_args

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = VirtualCenterEndpoint(**prov_config['endpoints']['default'])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(name=prov_config['name'],
                   endpoints={endpoint.name: endpoint},
                   zone=prov_config['server_zone'],
                   key=prov_key,
                   start_ip=start_ip,
                   end_ip=end_ip,
                   appliance=appliance)

    @property
    def view_value_mapping(self):
        return {'name': self.name,
                'prov_type': 'VMware vCenter'
                }
