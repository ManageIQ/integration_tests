"""
utils.hosts
--------------

"""
from fixtures import navigation
from utils import conf

HOST_TYPES = ('rhev', 'rhel', 'esx', 'esxi')
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'


def get_host_by_name(host_name):
    for provider in conf.cfme_data['management_systems']:
        for host in conf.cfme_data['management_systems'][provider].get('hosts', []):
            if host_name == host['name']:
                return host
    return None


def does_host_have_valid_creds(host_name):
    infra_hosts_pg = navigation.infra_hosts_pg()
    return infra_hosts_pg.quadicon_region.get_quadicon_by_title(host_name).valid_credentials


def add_host_credentials(host_name):
    '''Add host credentials
    '''
    infra_hosts_pg = navigation.infra_hosts_pg()
    host = get_host_by_name(host_name)
    host_detail_pg = infra_hosts_pg.edit_host_and_save(host)
    assert 'Host "%s" was saved' % host_name in host_detail_pg.flash.message,\
        FLASH_MESSAGE_NOT_MATCHED
    host_detail_pg.flash.click()
    return host_detail_pg


def setup_all_provider_hosts_credentials():
    for provider_key in conf.cfme_data['management_systems']:
        if 'hosts' in conf.cfme_data['management_systems'][provider_key]:
            for host in conf.cfme_data['management_systems'][provider_key]['hosts']:
                if not does_host_have_valid_creds(host['name']):
                    add_host_credentials(host['name'])


def setup_providers_hosts_credentials(provider_key):
    if provider_key in conf.cfme_data['management_systems']:
        if 'hosts' in conf.cfme_data['management_systems'][provider_key]:
            for host in conf.cfme_data['management_systems'][provider_key]['hosts']:
                if not does_host_have_valid_creds(host['name']):
                    add_host_credentials(host['name'])
