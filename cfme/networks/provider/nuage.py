import attr
from widgetastic.widget import View
from widgetastic_patternfly import Tab, BootstrapSelect, Input
from wrapanapi.nuage import NuageSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from cfme.common.provider_views import BeforeFillMixin
from cfme.networks.security_group import SecurityGroupCollection
from cfme.utils import version
from cfme.utils.varmeth import variable
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


@attr.s
class NuageProvider(NetworkProvider):
    """ Class representing network provider in sdn

    Note: Network provider can be added to cfme database
          only automaticaly with cloud provider
    """
    STATS_TO_MATCH = ['num_security_group', 'num_cloud_subnet']
    in_version = ('5.9', version.LATEST)
    type_name = 'nuage'
    db_types = ['Nuage::NetworkManager']
    endpoints_form = NuageEndpointForm
    mgmt_class = NuageSystem

    _collections = {
        'security_groups': SecurityGroupCollection,
    }

    endpoints = attr.ib(default=None)
    key = attr.ib(default=None)
    api_version = attr.ib(default=None)
    api_version_name = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.endpoints = self._prepare_endpoints(self.endpoints)
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
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = NuageEndpoint(**prov_config['endpoints']['default'])
        return cls(appliance, name=prov_config['name'],
                   endpoints={endpoint.name: endpoint},
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
        return int(self.get_detail('Relationships', 'Security Groups'))

    @variable(alias="db")
    def num_cloud_subnet(self):
        pass  # TODO: come up with a db query

    @num_cloud_subnet.variant('ui')
    def num_cloud_subnet_ui(self):
        return int(self.get_detail('Relationships', 'Cloud Subnets'))
