import copy

import attr
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from wrapanapi.systems import NuageSystem

from cfme.cloud.tenant import TenantCollection
from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.common.provider import EventsEndpoint
from cfme.common.provider_views import BeforeFillMixin
from cfme.networks.provider import NetworkProvider
from cfme.networks.security_group import SecurityGroupCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.varmeth import variable
from widgetastic_manageiq import RadioGroup
from widgetastic_manageiq import WaitTab


class NuageEndpoint(DefaultEndpoint):
    @property
    def view_value_mapping(self):
        return {'security_protocol': self.security_protocol,
                'hostname': self.hostname,
                'api_port': getattr(self, 'api_port', 5000)
                }


class NuageEndpointForm(View):
    @View.nested
    class default(WaitTab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        security_protocol = BootstrapSelect('default_security_protocol')
        api_port = Input('default_api_port')

    @View.nested
    class events(WaitTab, BeforeFillMixin):
        TAB_NAME = 'Events'
        event_stream = RadioGroup(locator='//div[@id="amqp"]')
        # below controls which appear only if amqp is chosen
        security_protocol = BootstrapSelect('amqp_security_protocol')
        hostname = Input('amqp_hostname')
        api_port = Input('amqp_api_port')
        username = Input('amqp_userid')
        password = Input('amqp_password')

        validate = Button('Validate')


@attr.s(eq=False)
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
    type_name = 'nuage'
    db_types = ['Nuage::NetworkManager']
    endpoints_form = NuageEndpointForm
    mgmt_class = NuageSystem
    settings_key = 'ems_nuage'
    log_name = 'nuage'

    _collections = {
        'security_groups': SecurityGroupCollection,
        'cloud_tenants': TenantCollection
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
    def from_config(cls, prov_config, prov_key, appliance=None):
        """
        Returns the NuageProvider object based on cfme_data.yaml and credentials.eyaml.

        Args:
            prov_config: corresponding section of cfme_data.yaml for this provider
            prov_key: key of this provider, as specified in cfme_data.yaml

        Returns: NuageProvider object filled with all the data
        """
        appliance = appliance or cls.appliance
        endpoints = {}
        for endp in prov_config['endpoints']:
            for expected_endpoint in (NuageEndpoint, EventsEndpoint):
                if expected_endpoint.name == endp:
                    endpoints[endp] = expected_endpoint(**prov_config['endpoints'][endp])

        return appliance.collections.network_providers.instantiate(
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
