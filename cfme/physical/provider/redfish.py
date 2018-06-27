import attr
import copy

from widgetastic_patternfly import BootstrapSelect, Input
from wrapanapi.systems import RedfishSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from . import PhysicalProvider


class RedfishEndpoint(DefaultEndpoint):
    api_port = 443
    security_protocol = 'SSL'

    @property
    def view_value_mapping(self):
        return {
            'security_protocol': self.security_protocol,
            'hostname': self.hostname,
            'api_port': self.api_port
        }


class RedfishEndpointForm(DefaultEndpointForm):
    security_protocol = BootstrapSelect('default_security_protocol')
    api_port = Input('default_api_port')


@attr.s(hash=False)
class RedfishProvider(PhysicalProvider):
    STATS_TO_MATCH = ['num_server']
    type_name = 'redfish'
    endpoints_form = RedfishEndpointForm
    string_name = 'Physical Infrastructure'
    mgmt_class = RedfishSystem
    refresh_text = "Refresh Relationships and Power States"
    db_types = ["Redfish::PhysicalInfraManager"]
    settings_key = 'ems_redfish'
    log_name = 'redfish'

    @property
    def mgmt(self):
        from cfme.utils.providers import get_mgmt
        d = copy.deepcopy(self.data)
        d['type'] = self.type_name
        d['hostname'] = self.default_endpoint.hostname
        d['api_port'] = self.default_endpoint.api_port
        d['security_protocol'] = self.default_endpoint.security_protocol
        d['credentials'] = self.default_endpoint.credentials
        return get_mgmt(d)

    @classmethod
    def from_config(cls, prov_config, prov_key):
        endpoint = RedfishEndpoint(**prov_config['endpoints']['default'])
        return cls.appliance.collections.physical_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            endpoints={endpoint.name: endpoint},
            key=prov_key)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Redfish'
        }
