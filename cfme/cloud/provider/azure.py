from mgmtsystem.azure import AzureSystem
from . import Provider


@Provider.add_type_map
class AzureProvider(Provider):
    type_name = "azure"
    mgmt_class = AzureSystem

    def __init__(self, name=None, credentials=None, zone=None, key=None, region=None,
                 tenant_id=None, subscription_id=None):
        super(AzureProvider, self).__init__(name=name, credentials=credentials,
                                            zone=zone, key=key)
        self.region = region
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id

    def _form_mapping(self, create=None, **kwargs):
        # Will still need to figure out where to put the tenant id.
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Azure',
                'region_select': kwargs.get('region'),
                'azure_tenant_id': kwargs.get('tenant_id'),
                'azure_subscription_id': kwargs.get('subscription_id')}

    @classmethod
    def configloader(cls, prov_config, prov_key):
        credentials_key = prov_config['credentials']
        credentials = cls.process_credential_yaml_key(credentials_key)
        return cls(name=prov_config['name'],
            tenant_id=prov_config['tenant_id'],
            subscription_id=prov_config['subscription_id'],
            credentials={'default': credentials},
            key=prov_key)
