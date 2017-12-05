import attr
from widgetastic.widget import View
from widgetastic_patternfly import Tab, BootstrapSelect, Input

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from cfme.common.provider_views import BeforeFillMixin
from cfme.networks.security_group import SecurityGroupCollection
from cfme.utils import version
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
    STATS_TO_MATCH = []
    in_version = ('5.9', version.LATEST)
    type_name = 'nuage'
    db_types = ['Nuage::NetworksManager']
    endpoints_form = NuageEndpointForm

    _collections = {
        'security_groups': SecurityGroupCollection,
    }

    endpoints = attr.ib(default=None)
    key = attr.ib(default=None)

    def __attrs_post_init__(self):
        self.endpoints = self._prepare_endpoints(self.endpoints)

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        endpoint = NuageEndpoint(**prov_config['endpoints']['default'])
        return cls(appliance, name=prov_config['name'],
                   endpoints={endpoint.name: endpoint},
                   key=prov_key)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'Nuage Network Manager'
        }
