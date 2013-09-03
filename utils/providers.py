from common import mgmt_system
from cfme_data import load_cfme_data
from credentials import load_credentials

provider_type_map = {
    'virtualcenter': mgmt_system.VMWareSystem,
    'rhevm': mgmt_system.RHEVMSystem,
}

def provider_factory(provider_name, providers=None, credentials=None):
    if providers is None:
        cfme_data = load_cfme_data()
        providers = cfme_data['management_systems']

    provider = providers[provider_name]

    if credentials is None:
        credentials_dict = load_credentials()
        credentials = credentials_dict[provider['credentials']]

    provider_instance = provider_type_map[provider['type']](
        provider['ipaddress'],
        credentials['username'],
        credentials['password']
    )

    return provider_instance
