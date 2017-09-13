from widgetastic_patternfly import BootstrapSelect, Input

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from . import InfraProvider
from wrapanapi.scvmm import SCVMMSystem


class SCVMMEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': self.hostname,
                'security_protocol': getattr(self, 'security_protocol', None),
                'realm': getattr(self, 'security_realm', None)
                }


class SCVMMEndpointForm(DefaultEndpointForm):
    security_protocol = BootstrapSelect(id='default_security_protocol')
    realm = Input('realm')  # appears when Kerberos is chosen in security_protocol


class SCVMMProvider(InfraProvider):
    STATS_TO_MATCH = ['num_template', 'num_vm']
    type_name = "scvmm"
    mgmt_class = SCVMMSystem
    db_types = ["Microsoft::InfraManager"]
    endpoints_form = SCVMMEndpointForm
    discover_dict = {"scvmm": True}
    bad_credentials_error_msg = (
        'Credential validation was not successful: '
        'Unable to connect: WinRM::WinRMAuthorizationError'
    )

    def __init__(self, name=None, endpoints=None, key=None, zone=None, hostname=None,
                 ip_address=None, start_ip=None, end_ip=None, provider_data=None, appliance=None):
        super(SCVMMProvider, self).__init__(
            name=name, endpoints=endpoints, zone=zone, key=key, provider_data=provider_data,
            appliance=appliance)
        self.hostname = hostname
        self.start_ip = start_ip
        self.end_ip = end_ip
        if ip_address:
            self.ip_address = ip_address

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Microsoft System Center VMM',
        }

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        values = {}
        if 'host_group' not in deploy_args:
            values['host_group'] = self.data.get("host_group", "All Hosts")
        if 'cpu' not in deploy_args:
            values['cpu'] = self.data.get("cpu", 0)
        if 'ram' not in deploy_args:
            values['ram'] = self.data.get("ram", 0)
        return values

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = SCVMMEndpoint(**prov_config['endpoints']['default'])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return cls(
            name=prov_config['name'],
            endpoints={endpoint.name: endpoint},
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip,
            appliance=appliance)
