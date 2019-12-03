import attr
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from wrapanapi.systems import EC2System

from cfme.cloud.instance.ec2 import EC2Instance
from cfme.cloud.provider import CloudProvider
from cfme.common.candu_views import AzoneCloudUtilizationView
from cfme.common.candu_views import VMUtilizationView
from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.common.provider import SmartStateDockerEndpoint
from cfme.common.provider_views import BeforeFillMixin
from cfme.services.catalogs.catalog_items import AmazonCatalogItem
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import LineChart
from widgetastic_manageiq import WaitTab


class EC2Endpoint(DefaultEndpoint):
    """
     represents default Amazon endpoint (Add/Edit dialogs)
    """
    @property
    def view_value_mapping(self):
        return {'endpoint_url': getattr(self, 'endpoint_url', None),
                'assume_role_arn': getattr(self, 'assume_role_arn', None)}


class EC2EndpointForm(View):
    """
     represents default EC2 endpoint form in UI (Add/Edit dialogs)
    """
    @View.nested
    class default(WaitTab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'

        endpoint_url = Input('default_url')
        assume_role_arn = Input('default_assume_role')

    @View.nested
    class smartstate(WaitTab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'SmartState Docker'

        username = Input(id='smartstate_docker_userid')
        password = Input(id='smartstate_docker_password')
        change_password = Text(
            locator='.//a[normalize-space(.)="Change stored SmartState Docker password"]')

        validate = Button('Validate')


class EC2InstanceUtilizationView(VMUtilizationView):
    """A VM Utilization view for AWS providers"""
    vm_cpu = LineChart(id='miq_chart_parent_candu_0')
    vm_disk = LineChart(id='miq_chart_parent_candu_1')
    vm_network = LineChart(id='miq_chart_parent_candu_2')


class EC2AzoneUtilizationView(AzoneCloudUtilizationView):
    """Availability zone Utilization view for AWS providers"""
    azone_disk = LineChart(id='miq_chart_parent_candu_1')
    azone_network = LineChart(id='miq_chart_parent_candu_2')
    azone_network_avg = LineChart(id='miq_chart_parent_candu_2_2')
    azone_instance = VersionPicker({
        Version.lowest(): LineChart(id='miq_chart_parent_candu_4'),
        '5.10': LineChart(id='miq_chart_parent_candu_3')
    })


@attr.s(eq=False)
class EC2Provider(CloudProvider):
    """
     BaseProvider->CloudProvider->EC2Provider class.
     represents CFME provider and operations available in UI
    """
    catalog_item_type = AmazonCatalogItem
    vm_utilization_view = EC2InstanceUtilizationView
    azone_utilization_view = EC2AzoneUtilizationView
    type_name = "ec2"
    mgmt_class = EC2System
    vm_class = EC2Instance
    db_types = ["Amazon::CloudManager"]
    endpoints_form = EC2EndpointForm
    discover_name = "Amazon EC2"
    settings_key = 'ems_amazon'
    log_name = 'aws'
    ems_pretty_name = 'Amazon EC2'

    region = attr.ib(default=None)
    region_name = attr.ib(default=None)

    @property
    def view_value_mapping(self):
        """Maps values to view attrs"""
        return {
            'name': self.name,
            'prov_type': 'Amazon EC2',
            'region': self.region_name,
        }

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        """Returns the EC" object from configuration"""
        appliance = appliance or cls.appliance
        endpoints = {}
        for endp in prov_config['endpoints']:
            for expected_endpoint in (EC2Endpoint, SmartStateDockerEndpoint):
                if expected_endpoint.name == endp:
                    endpoints[endp] = expected_endpoint(**prov_config['endpoints'][endp])

        region_name = prov_config["region_name"]
        # Note: for Version 5.10 "Northern" replace with "N." like US West (N. California)
        if appliance.version >= "5.10":
            region_name = region_name.replace("Northern", "N.")

        return appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            region=prov_config['region'],
            region_name=region_name,
            endpoints=endpoints,
            zone=prov_config['server_zone'],
            key=prov_key)

    @staticmethod
    def discover_dict(credential):
        """Returns the discovery credentials dictionary"""
        return {
            'username': getattr(credential, 'principal', None),
            'password': getattr(credential, 'secret', None),
            'confirm_password': getattr(credential, 'verify_secret', None)
        }
