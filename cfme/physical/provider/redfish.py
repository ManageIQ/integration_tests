import attr
import copy

from widgetastic_patternfly import BootstrapSelect, Input
from widgetastic.exceptions import NoSuchElementException
from wrapanapi.systems import RedfishSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from cfme.physical.physical_server import (
    PhysicalServer,
    PhysicalServerCollection)
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.varmeth import variable
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
    STATS_TO_MATCH = ['num_server', 'num_chassis', 'num_racks']
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

    def get_detail(self, label):
        view = navigate_to(self, 'Details')
        try:
            stat = view.entities.summary('Relationships').get_text_of(label)
            logger.info("{}: {}".format(label, stat))
        except NoSuchElementException:
            logger.error("Couldn't find number of {}".format(label))
        return stat

    @variable(alias='ui')
    def num_chassis(self):
        return int(self.get_detail('Physical Chassis'))

    @variable(alias='ui')
    def num_racks(self):
        return int(self.get_detail('Physical Racks'))


@attr.s
class RedfishPhysicalServer(PhysicalServer):

    INVENTORY_TO_MATCH = ['power_state']
    STATS_TO_MATCH = ['cores_capacity', 'memory_capacity']


@attr.s
class RedfishPhysicalServerCollection(PhysicalServerCollection):
    ENTITY = RedfishPhysicalServer
