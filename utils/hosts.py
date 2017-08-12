"""
utils.hosts
--------------

"""
import socket

from utils import conf
from utils.log import logger
from utils.wait import wait_for
from utils.update import update
from cfme.infrastructure import host
import cfme.fixtures.pytest_selenium as sel


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


def setup_host_creds(provider_key, host_name, remove_creds=False, ignore_errors=False):
    try:
        host_data = get_host_data_by_name(provider_key, host_name)
        test_host = host.Host(name=host_name)
        if not test_host.has_valid_credentials:
            logger.info("Setting up creds for host: %s", host_name)
            with update(test_host):
                if test_host.ip_address is None:
                    test_host.ip_address = socket.gethostbyname_ex(host_name)[2][0]
                test_host.credentials = host.get_credentials_from_config(host_data['credentials'])
            wait_for(
                lambda: test_host.has_valid_credentials,
                delay=10,
                num_sec=120,
                fail_func=sel.refresh
            )
        elif test_host.has_valid_credentials and remove_creds:
            with update(test_host):
                test_host.credentials = host.Host.Credential(principal="", secret="",
                    verify_secret="")
    except Exception as e:
        if not ignore_errors:
            raise e


def setup_all_provider_hosts_credentials():
    for provider_key in conf.cfme_data.get('management_systems', {}):
        if 'hosts' in conf.cfme_data.get('management_systems', {})[provider_key]:
            for yamlhost in conf.cfme_data.get('management_systems', {})[provider_key]['hosts']:
                setup_host_creds(provider_key, yamlhost['name'])


def setup_providers_hosts_credentials(provider_key, ignore_errors=False):
    if provider_key in conf.cfme_data.get('management_systems', {}):
        if 'hosts' in conf.cfme_data.get('management_systems', {})[provider_key]:
            for yamlhost in conf.cfme_data.get('management_systems', {})[provider_key]['hosts']:
                setup_host_creds(provider_key, yamlhost['name'], ignore_errors=ignore_errors)
