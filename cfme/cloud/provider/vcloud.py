import attr
from widgetastic.widget import View
from widgetastic_patternfly import Input
from wrapanapi.systems import VmwareCloudSystem

from cfme.cloud.provider import CloudProvider
from cfme.common.provider import Credential
from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.common.provider_views import BeforeFillMixin
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.varmeth import variable
from widgetastic_manageiq import WaitTab


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
    class default(WaitTab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        api_port = Input('default_api_port')


@attr.s(cmp=False)
class VmwareCloudProvider(CloudProvider):
    STATS_TO_MATCH = ['num_availability_zone', 'num_orchestration_stack', 'num_vm']
    type_name = "vcloud"
    mgmt_class = VmwareCloudSystem
    db_types = ["Vmware::CloudManager"]
    endpoints_form = VmwareCloudEndpointForm

    api_version = attr.ib(default=None)
    api_version_name = attr.ib(default=None)

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
        appliance = appliance if appliance is not None else cls.appliance
        endpoint = VmwareCloudEndpoint(**prov_config['endpoints']['default'])
        return appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
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
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Availability Zones"))

    @variable(alias="db")
    def num_orchestration_stack(self):
        pass  # TODO: come up with a db query

    @num_orchestration_stack.variant('ui')
    def num_orchestration_stack_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Orchestration Stacks"))
