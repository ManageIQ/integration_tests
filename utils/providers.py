from cfme_data import load_cfme_data
from credentials import load_credentials
from utils import mgmt_system


# infra and cloud provider type maps, useful for type checking
infra_provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
}

cloud_provider_type_map = {
    'ec2': mgmt_system.EC2System,
    'openstack': mgmt_system.OpenstackSystem,
}

# Combined type map, provider_factory doesn't discriminate
provider_type_map = dict(
    infra_provider_type_map.items() + cloud_provider_type_map.items()
)


def provider_factory(provider_name, providers=None, credentials=None):
    if providers is None:
        cfme_data = load_cfme_data()
        providers = cfme_data['management_systems']

    provider = providers[provider_name]

    if credentials is None:
        credentials_dict = load_credentials()
        credentials = credentials_dict[provider['credentials']]

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider.copy()
    provider_kwargs.update(credentials)
    provider_instance = provider_type_map[provider['type']](**provider_kwargs)
    return provider_instance
