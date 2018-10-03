import attr
import copy
from widgetastic.widget import View
from widgetastic_patternfly import Tab, BootstrapSelect, Input, Button
from wrapanapi.systems import NuageSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm, EventsEndpoint
from cfme.common.provider_views import BeforeFillMixin
from cfme.networks.security_group import SecurityGroupCollection
from cfme.networks.cloud_tenant import CloudTenant, CloudTenantCollection
from cfme.networks.subnet import Subnet, SubnetCollection
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.varmeth import variable
from widgetastic_manageiq import RadioGroup
from . import NetworkProvider


class NuageEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'security_protocol': self.security_protocol,
                'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', 5000)
                }


class NuageEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        security_protocol = BootstrapSelect('default_security_protocol')
        api_port = Input('default_api_port')

    @View.nested
    class events(Tab, BeforeFillMixin):
        TAB_NAME = 'Events'
        event_stream = RadioGroup(locator='//div[@id="amqp"]')
        # below controls which appear only if amqp is chosen
        security_protocol = BootstrapSelect('amqp_security_protocol')
        hostname = Input('amqp_hostname')
        api_port = Input('amqp_api_port')
        username = Input('amqp_userid')
        password = Input('amqp_password')

        validate = Button('Validate')


class ValidateStatsMixin(object):
    def validate_stats(self, expected_stats):
        """ Validates that the details page matches the subnet's inventory.

        Args:
            expected_stats: dictionary of values to be compered to UI values,
            where keys have the same names as NuageSubnet ui functions

        This method is given expected stats as an argument and those are then matched
        against the UI. An AssertionError exception will be raised if the stats retrieved
        from the UI do not match those from expected stats.

        IMPORTANT: Please make sure NuageSubnet implements counterpart ui method for each of
        the keys in expected_stats dictionary.
        """

        # Make sure we are on the subnet details page and refresh it
        navigate_to(self, "DetailsThroughProvider")
        self.browser.selenium.refresh()

        cfme_stats = {stat: getattr(self, stat)(method='ui') for stat in expected_stats}
        assert cfme_stats == expected_stats


@attr.s(hash=False)
class NuageProvider(NetworkProvider):
    """ Class representing network provider in sdn

    Note: Network provider can be added to cfme database
          only automaticaly with cloud provider
    """
    STATS_TO_MATCH = ['num_security_group',
                      'num_cloud_subnet',
                      'num_cloud_tenant',
                      'num_network_router',
                      'num_cloud_network',
                      'num_floating_ip',
                      'num_network_port']
    in_version = ('5.9', version.LATEST)
    type_name = 'nuage'
    db_types = ['Nuage::NetworkManager']
    endpoints_form = NuageEndpointForm
    mgmt_class = NuageSystem
    settings_key = 'ems_nuage'
    log_name = 'nuage'

    _collections = {
        'security_groups': SecurityGroupCollection,
    }

    key = attr.ib(default=None)
    api_version = attr.ib(default=None)
    api_version_name = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.parent = self.appliance.collections.network_providers

    @property
    def mgmt(self):
        from cfme.utils.providers import get_mgmt
        d = copy.deepcopy(self.data)
        d['hostname'] = self.default_endpoint.hostname
        d['api_port'] = self.default_endpoint.api_port
        d['security_protocol'] = self.default_endpoint.security_protocol
        d['username'] = self.default_endpoint.credentials.principal
        d['password'] = self.default_endpoint.credentials.secret
        return get_mgmt(d)

    @classmethod
    def from_config(cls, prov_config, prov_key):
        """
        Returns the NuageProvider object based on cfme_data.yaml and credentials.eyaml.

        Args:
            prov_config: corresponding section of cfme_data.yaml for this provider
            prov_key: key of this provider, as specified in cfme_data.yaml

        Returns: NuageProvider object filled with all the data
        """
        endpoints = {}
        for endp in prov_config['endpoints']:
            for expected_endpoint in (NuageEndpoint, EventsEndpoint):
                if expected_endpoint.name == endp:
                    endpoints[endp] = expected_endpoint(**prov_config['endpoints'][endp])

        return cls.appliance.collections.network_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            endpoints=endpoints,
            api_version=prov_config['api_version'],
            api_version_name=prov_config['api_version_name'],
            key=prov_key)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Nuage Network Manager',
            'api_version': self.api_version_name
        }

    @variable(alias="ui")
    def num_security_group(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Security Groups"))

    @variable(alias="ui")
    def num_cloud_subnet(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Cloud Subnets"))

    @variable(alias="ui")
    def num_cloud_tenant(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Cloud Tenants"))

    @variable(alias="ui")
    def num_network_router(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Network Routers"))

    @variable(alias="ui")
    def num_cloud_network(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Cloud Networks"))

    @variable(alias="ui")
    def num_floating_ip(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Floating IPs"))

    @variable(alias="ui")
    def num_network_port(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Network Ports"))


@attr.s
class NuageSubnet(Subnet, ValidateStatsMixin):
    ems_ref = attr.ib(default=None)

    @variable(alias="ui")
    def name_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('Name')

    @variable(alias="ui")
    def type_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('Type')

    @variable(alias="ui")
    def cidr_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('CIDR')

    @variable(alias="ui")
    def gateway_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('Gateway')

    @variable(alias="ui")
    def network_protocol_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('Network protocol')

    @variable(alias="ui")
    def network_manager_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.relationships.get_text_of('Network Manager')

    @variable(alias="ui")
    def cloud_tenant_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.relationships.get_text_of('Cloud tenant')

    @variable(alias="ui")
    def network_router_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.relationships.get_text_of('Network Router')

    @variable(alias="ui")
    def network_ports_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Network Ports'))

    @variable(alias="ui")
    def security_groups_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Security Groups'))


@attr.s
class NuageSubnetCollection(SubnetCollection):
    ENTITY = NuageSubnet

    def find_by_ems_ref(self, ems_ref, provider):
        """Fetch NuageSubnet instance with provided ems_ref"""
        subnets_table = self.appliance.db.client['cloud_subnets']
        subnet = (self.appliance.db.client.session
                  .query(subnets_table.name, subnets_table.ems_ref)
                  .filter(subnets_table.ems_ref == ems_ref).first())

        return self.instantiate(
            name=subnet.name,
            ems_ref=subnet.ems_ref,
            provider_obj=provider
        ) if subnet else None


@attr.s
class NuageCloudTenant(CloudTenant, ValidateStatsMixin):
    ems_ref = attr.ib(default=None)
    provider_obj = attr.ib(default=None)

    @variable(alias="ui")
    def name_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.properties.get_text_of('Name')

    @variable(alias="ui")
    def network_manager_value(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return view.entities.relationships.get_text_of('Network Manager')

    @variable(alias="ui")
    def cloud_subnets_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Cloud Subnets'))

    @variable(alias="ui")
    def network_routers_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Network Routers'))

    @variable(alias="ui")
    def security_groups_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Security Groups'))

    @variable(alias="ui")
    def floating_ips_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Floating IPs'))

    @variable(alias="ui")
    def network_ports_num(self):
        view = navigate_to(self, 'DetailsThroughProvider')
        return int(view.entities.relationships.get_text_of('Network Ports'))


@attr.s
class NuageCloudTenantCollection(CloudTenantCollection):
    ENTITY = NuageCloudTenant

    def find_by_ems_ref(self, ems_ref, provider):
        """Fetch NuageCloudTenant instance with provided ems_ref"""
        tenants_table = self.appliance.db.client['cloud_tenants']
        tenant = (self.appliance.db.client.session
                  .query(tenants_table.name, tenants_table.ems_ref)
                  .filter(tenants_table.ems_ref == ems_ref).first())

        return self.instantiate(
            name=tenant.name,
            ems_ref=tenant.ems_ref,
            provider_obj=provider
        ) if tenant else None
