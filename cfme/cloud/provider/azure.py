from wrapanapi.msazure import AzureSystem

from . import CloudProvider
from cfme.common.provider import DefaultEndpoint, DefaultEndpointForm
from cfme.utils.version import pick


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


class AzureProvider(CloudProvider):
    """
     BaseProvider->CloudProvider->AzureProvider class.
     represents CFME provider and operations available in UI
    """
    type_name = "azure"
    mgmt_class = AzureSystem
    db_types = ["Azure::CloudManager"]
    endpoints_form = AzureEndpointForm
    discover_name = "Azure"

    def __init__(self, name=None, endpoints=None, zone=None, key=None, region=None,
                 tenant_id=None, subscription_id=None, appliance=None):
        super(AzureProvider, self).__init__(name=name, endpoints=endpoints,
                                            zone=zone, key=key, appliance=appliance)
        self.region = region  # Region can be a string or a dict for version pick
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    @property
    def view_value_mapping(self):
        """Maps values to view attrs"""
        region = pick(self.region) if isinstance(self.region, dict) else self.region
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
        endpoint = AzureEndpoint(**prov_config['endpoints']['default'])
        # HACK: stray domain entry in credentials, so ensure it is not there
        endpoint.credentials.domain = None
        return cls(
            name=prov_config['name'],
            region=prov_config.get('region'),
            tenant_id=prov_config['tenant_id'],
            subscription_id=prov_config['subscription_id'],
            endpoints={endpoint.name: endpoint},
            key=prov_key,
            appliance=appliance)

    @staticmethod
    def discover_dict(credential):
        """Returns the discovery credentials dictionary"""
        return {
            'client_id': getattr(credential, 'principal', None),
            'client_key': getattr(credential, 'secret', None),
            'tenant_id': getattr(credential, 'tenant_id', None),
            'subscription': getattr(credential, 'subscription_id', None)
        }
