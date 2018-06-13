"""
utils.hosts
--------------

"""
import socket

from cfme.utils import conf
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.infrastructure import host


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


def setup_host_creds(provider, host_name, remove_creds=False, ignore_errors=False):
    try:
        appliance = provider.appliance
        host_data = get_host_data_by_name(provider.key, host_name)
        if host_data is None:
            raise ValueError(
                'There is no {} host entry for provider {}!'.format(host_name, provider.key))
        test_host_collection = appliance.collections.hosts
        test_host = test_host_collection.instantiate(name=host_name)
        if not test_host.has_valid_credentials:
            logger.info("Setting up creds for host: %s", host_name)
            with update(test_host):
                if test_host.ip_address is None:
                    test_host.ip_address = socket.gethostbyname_ex(host_name)[2][0]
                test_host.credentials = host.Host.get_credentials_from_config(
                    host_data['credentials'])
        elif test_host.has_valid_credentials and remove_creds:
            with update(test_host):
                test_host.credentials = host.Host.Credential(principal="", secret="",
                                                             verify_secret="")
    except Exception:
        if not ignore_errors:
            raise


def setup_providers_hosts_credentials(provider, ignore_errors=False):
    for yamlhost in provider.data.get('hosts', []):
        setup_host_creds(provider, yamlhost['name'], ignore_errors=ignore_errors)
