"""
utils.physical_servers
--------------

"""
from cfme.utils import conf


def get_physical_server_data_by_name(provider_key, physical_server_name):
    providers = conf.cfme_data.get('management_systems', {})[provider_key]
    physical_servers = providers.get('physical_servers', [])
    for physical_server_obj in physical_servers:
        if physical_server_name == physical_server_obj['name']:
            return physical_server_obj
    return None
