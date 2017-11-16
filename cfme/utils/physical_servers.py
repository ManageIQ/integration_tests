"""
utils.hosts
--------------

"""
import socket

from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.infrastructure import physical_server


def get_physical_server_data_by_name(provider_key, physical_server_name):
    for physical_server_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('physical_servers', []):
        if physical_server__name == physical_server_obj['name']:
            return physical_server_obj
    return None
