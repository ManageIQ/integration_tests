import copy

import attr
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Input
from wrapanapi.systems import RedfishSystem

from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.exceptions import HostStatsNotContains
from cfme.exceptions import ProviderHasNoProperty
from cfme.exceptions import StatsDoNotMatch
from cfme.physical.physical_chassis import PhysicalChassis
from cfme.physical.physical_chassis import PhysicalChassisCollection
from cfme.physical.physical_rack import PhysicalRack
from cfme.physical.physical_rack import PhysicalRackCollection
from cfme.physical.physical_server import PhysicalServer
from cfme.physical.physical_server import PhysicalServerCollection
from cfme.physical.provider import PhysicalProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.varmeth import variable


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


@attr.s(cmp=False)
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
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance if appliance is not None else cls.appliance
        endpoint = RedfishEndpoint(**prov_config['endpoints']['default'])
        return appliance.collections.physical_providers.instantiate(
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


@attr.s
class RedfishPhysicalChassis(PhysicalChassis):
    INVENTORY_TO_MATCH = ['chassis_name', 'description', 'identify_led_state']
    STATS_TO_MATCH = ['num_physical_servers']

    def __init__(self):
        super(RedfishPhysicalChassis, self)


@attr.s
class RedfishPhysicalChassisCollection(PhysicalChassisCollection):
    ENTITY = RedfishPhysicalChassis


@attr.s
class RedfishPhysicalRack(PhysicalRack):
    INVENTORY_TO_MATCH = ["rack_name"]
    STATS_TO_MATCH = []

    def __init__(self):
        super(RedfishPhysicalRack, self)

    def validate_stats(self, ui=False):
        """ Validates that the detail page matches the physical rack's information.

        This method logs into the provider using the mgmt_system interface and collects
        a set of statistics to be matched against the UI. An exception will be raised
        if the stats retrieved from the UI do not match those retrieved from wrapanapi.
        """

        # Make sure we are on the physical rack detail page
        if ui:
            self.load_details()

        # Retrieve the client and the stats and inventory to match
        client = self.provider.mgmt
        stats_to_match = self.STATS_TO_MATCH
        inventory_to_match = self.INVENTORY_TO_MATCH

        # Retrieve the stats and inventory from wrapanapi
        rack_stats = client.rack_stats(self, stats_to_match)
        rack_inventory = client.rack_inventory(self, inventory_to_match)

        # Refresh the browser
        if ui:
            self.browser.selenium.refresh()

        # Verify that the stats retrieved from wrapanapi match those retrieved
        # from the UI
        for stat in stats_to_match:
            try:
                cfme_stat = int(getattr(self, stat)(method='ui' if ui else None))
                rack_stat = int(rack_stats[stat])

                if rack_stat != cfme_stat:
                    msg = "The {} stat does not match. (server: {}, server stat: {}, cfme stat: {})"
                    raise StatsDoNotMatch(msg.format(stat, self.name, rack_stat, cfme_stat))
            except KeyError:
                raise HostStatsNotContains(
                    "Server stats information does not contain '{}'".format(stat))
            except AttributeError:
                raise ProviderHasNoProperty("Provider does not know how to get '{}'".format(stat))

        # Verify that the inventory retrieved from wrapanapi match those retrieved
        # from the UI
        for inventory in inventory_to_match:
            try:
                cfme_inventory = getattr(self, inventory)(method='ui' if ui else None)
                rack_inventory = rack_inventory[inventory]

                if rack_inventory != cfme_inventory:
                    msg = "The {} inventory does not match. (server: {}, server inventory: {}, " \
                          "cfme inventory: {})"
                    raise StatsDoNotMatch(msg.format(inventory, self.name, rack_inventory,
                                                     cfme_inventory))
            except KeyError:
                raise HostStatsNotContains(
                    "Server inventory information does not contain '{}'".format(inventory))
            except AttributeError:
                msg = "Provider does not know how to get '{}'"
                raise ProviderHasNoProperty(msg.format(inventory))


@attr.s
class RedfishPhysicalRackCollection(PhysicalRackCollection):
    ENTITY = RedfishPhysicalRack
