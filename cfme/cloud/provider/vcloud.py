from widgetastic.widget import View
from widgetastic_patternfly import Tab, Input
from wrapanapi.vcloud import VmwareCloudSystem

from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm, Credential
from cfme.common.provider_views import BeforeFillMixin
from cfme.utils import version
from cfme.utils.varmeth import variable
from . import CloudProvider


class VmwareCloudCredential(Credential):
    def __init__(self, organization=None, **kwargs):
        super(VmwareCloudCredential, self).__init__(**kwargs)
        self.organization = organization

    @property
    def view_value_mapping(self):
        d = super(VmwareCloudCredential, self).view_value_mapping
        d['username'] = '{}@{}'.format(self.principal, self.organization)
        return d


class VmwareCloudEndpoint(DefaultEndpoint):
    credential_class = VmwareCloudCredential

    @property
    def view_value_mapping(self):
        return {
            'hostname': self.hostname,
            'api_port': self.api_port
        }


class VmwareCloudEndpointForm(View):
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        api_port = Input('default_api_port')


class VmwareCloudProvider(CloudProvider):
    STATS_TO_MATCH = ['num_availability_zone', 'num_orchestration_stack', 'num_vm']
    in_version = ('5.9', version.LATEST)
    type_name = "vcloud"
    mgmt_class = VmwareCloudSystem
    db_types = ["Vmware::CloudManager"]
    endpoints_form = VmwareCloudEndpointForm

    def __init__(self, api_version=None, api_version_name=None, **kwargs):
        super(VmwareCloudProvider, self).__init__(**kwargs)
        self.api_version = api_version
        self.api_version_name = api_version_name

    @property
    def mgmt(self):
        from cfme.utils.providers import get_mgmt
        d = self.data
        d['hostname'] = self.default_endpoint.hostname
        d['api_port'] = self.default_endpoint.api_port
        d['username'] = self.default_endpoint.credentials.principal
        d['organization'] = self.default_endpoint.credentials.organization
        d['password'] = self.default_endpoint.credentials.secret
        return get_mgmt(d)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': 'VMware vCloud',
            'vmware_cloud_api_version': self.api_version_name
        }

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        """Returns the vcloud object from configuration"""
        endpoint = VmwareCloudEndpoint(**prov_config['endpoints']['default'])
        return cls(appliance=appliance,
                   name=prov_config['name'],
                   endpoints={endpoint.name: endpoint},
                   api_version=prov_config['api_version'],
                   api_version_name=prov_config['api_version_name'],
                   key=prov_key)

    @variable(alias="db")
    def num_availability_zone(self):
        pass  # TODO: come up with a db query

    @num_availability_zone.variant('ui')
    def num_availability_zone_ui(self):
        return int(self.get_detail("Relationships", "Availability Zones"))

    @variable(alias="db")
    def num_orchestration_stack(self):
        pass  # TODO: come up with a db query

    @num_orchestration_stack.variant('ui')
    def num_orchestration_stack_ui(self):
        return int(self.get_detail("Relationships", "Orchestration Stacks"))
