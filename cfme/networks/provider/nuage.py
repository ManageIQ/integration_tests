import attr
from widgetastic.widget import View
from widgetastic_patternfly import Tab, BootstrapSelect, Input, Button
from wrapanapi.nuage import NuageSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm, EventsEndpoint
from cfme.common.provider_views import BeforeFillMixin
from cfme.networks.security_group import SecurityGroupCollection
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


@attr.s(hash=False)
class NuageProvider(NetworkProvider):
    """ Class representing network provider in sdn

    Note: Network provider can be added to cfme database
          only automaticaly with cloud provider
    """
    STATS_TO_MATCH = ['num_security_group',
                      'num_cloud_subnet',
                      'num_cloud_tenant',
                      'num_network_router']
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
        d = self.data
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

    @variable(alias="db")
    def num_security_group(self):
        pass  # TODO: come up with a db query

    @num_security_group.variant('ui')
    def num_security_group_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Security Groups"))

    @variable(alias="db")
    def num_cloud_subnet(self):
        pass  # TODO: come up with a db query

    @num_cloud_subnet.variant('ui')
    def num_cloud_subnet_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Cloud Subnets"))

    @variable(alias="db")
    def num_cloud_tenant(self):
        pass  # TODO: come up with a db query

    @num_cloud_tenant.variant('ui')
    def num_cloud_tenant_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Cloud Tenants"))

    @variable(alias="db")
    def num_network_router(self):
        pass  # TODO: come up with a db query

    @num_network_router.variant('ui')
    def num_network_router_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Network Routers"))
