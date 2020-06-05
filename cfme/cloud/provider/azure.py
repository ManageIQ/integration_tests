import attr
from wrapanapi.systems import AzureSystem

from cfme.cloud.instance.azure import AzureInstance
from cfme.cloud.provider import CloudProvider
from cfme.common.provider import BaseProvider
from cfme.common.provider import DefaultEndpoint
from cfme.common.provider import DefaultEndpointForm
from cfme.infrastructure.provider.rhevm import RHEVMVMUtilizationView
from cfme.services.catalogs.catalog_items import AzureCatalogItem
from cfme.utils.version import VersionPicker


class AzureEndpoint(DefaultEndpoint):
    """
     represents default Azure endpoint (Add/Edit dialogs)
    """
    @property
    def view_value_mapping(self):
        return {}


class AzureEndpointForm(DefaultEndpointForm):
    """
     represents default Azure endpoint form in UI (Add/Edit dialogs)
    """
    pass


class AzureInstanceUtilizationView(RHEVMVMUtilizationView):
    """A VM Utilization view for Azure providers"""
    pass


@attr.s(eq=False)
class AzureProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->AzureProvider class.
     represents CFME provider and operations available in UI
    """
    catalog_item_type = AzureCatalogItem
    vm_utilization_view = AzureInstanceUtilizationView
    type_name = "azure"
    mgmt_class = AzureSystem
    vm_class = AzureInstance
    db_types = ["Azure::CloudManager"]
    endpoints_form = AzureEndpointForm
    discover_name = "Azure"
    settings_key = 'ems_azure'
    log_name = 'azure'
    ems_pretty_name = 'Azure'

    region = attr.ib(default=None)
    tenant_id = attr.ib(default=None)
    subscription_id = attr.ib(default=None)
    provisioning_dialog_widget_names = (BaseProvider
            .provisioning_dialog_widget_names.difference('volumes'))

    @property
    def view_value_mapping(self):
        """Maps values to view attrs"""
        if isinstance(self.region, dict):
            region = VersionPicker(self.region).pick(self.appliance.version)
        else:
            region = self.region
        return {
            'name': self.name,
            'prov_type': 'Azure',
            'region': region,
            'tenant_id': self.tenant_id,
            'subscription': getattr(self, 'subscription_id', None)
        }

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        return self.data['provisioning']

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance or cls.appliance
        endpoint = AzureEndpoint(**prov_config['endpoints']['default'])
        # HACK: stray domain entry in credentials, so ensure it is not there
        endpoint.credentials.domain = None
        return appliance.collections.cloud_providers.instantiate(
            prov_class=cls,
            name=prov_config['name'],
            region=prov_config.get('region'),
            tenant_id=prov_config['tenant_id'],
            subscription_id=prov_config['subscription_id'],
            endpoints={endpoint.name: endpoint},
            key=prov_key)

    @staticmethod
    def discover_dict(credential):
        """Returns the discovery credentials dictionary"""
        return {
            'client_id': getattr(credential, 'principal', None),
            'client_key': getattr(credential, 'secret', None),
            'tenant_id': getattr(credential, 'tenant_id', None),
            'subscription': getattr(credential, 'subscription_id', None)
        }
