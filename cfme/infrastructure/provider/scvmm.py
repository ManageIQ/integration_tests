import attr
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Input
from wrapanapi.systems import SCVMMSystem

from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_items import SCVMMCatalogItem


class SCVMMEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'hostname': getattr(self, 'hostname', None),
                'security_protocol': getattr(self, 'security_protocol', None),
                'realm': getattr(self, 'security_realm', None)
                }


class SCVMMEndpointForm(DefaultEndpointForm):
    security_protocol = BootstrapSelect(id='default_security_protocol')
    realm = Input('realm')  # appears when Kerberos is chosen in security_protocol


@attr.s(cmp=False)
class SCVMMProvider(InfraProvider):
    catalog_item_type = SCVMMCatalogItem
    STATS_TO_MATCH = ['num_template', 'num_vm']
    type_name = "scvmm"
    mgmt_class = SCVMMSystem
    db_types = ["Microsoft::InfraManager"]
    endpoints_form = SCVMMEndpointForm
    ems_pretty_name = 'Microsoft System Center VMM'
    discover_dict = {"scvmm": True}
    bad_credentials_error_msg = (
        'Credential validation was not successful: '
        'Unable to connect: WinRM::WinRMAuthorizationError'
    )
    settings_key = 'ems_scvmm'
    ui_prov_type = 'Microsoft System Center VMM'
    log_name = 'scvmm'

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
        appliance = appliance or cls.appliance
        endpoint = SCVMMEndpoint(**prov_config['endpoints']['default'])

        if prov_config.get('discovery_range'):
            start_ip = prov_config['discovery_range']['start']
            end_ip = prov_config['discovery_range']['end']
        else:
            start_ip = end_ip = prov_config.get('ipaddress')
        return appliance.collections.infra_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            endpoints={endpoint.name: endpoint},
            key=prov_key,
            start_ip=start_ip,
            end_ip=end_ip)
