from . import CloudProvider
from utils.version import pick
from mgmtsystem.azure import AzureSystem


@CloudProvider.add_provider_type
class AzureProvider(CloudProvider):
    type_name = "azure"
    mgmt_class = AzureSystem

    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None,
                 tenant_id=None, subscription_id=None):
        super(AzureProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key)
        self.region = region  # Region can be a string or a dict for version pick
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    def _form_mapping(self, create=None, **kwargs):
        region = kwargs.get('region')
        if isinstance(region, dict):
            region = pick(region)
        # Will still need to figure out where to put the tenant id.
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Azure',
                'region_select': region,
                'azure_tenant_id': kwargs.get('tenant_id'),
                'azure_subscription_id': kwargs.get('subscription_id')}

    def deployment_helper(self, deploy_args):
        """ Used in utils.virtual_machines """
        return self.data['provisioning']

    @classmethod
    def from_config(cls, prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        # HACK: stray domain entry in credentials, so ensure it is not there
        credentials.domain = None
        return cls(
            name=prov_config['name'],
            region=prov_config.get('region'),
            tenant_id=prov_config['tenant_id'],
            subscription_id=prov_config['subscription_id'],
            credentials={'default': credentials},
            key=prov_key)
