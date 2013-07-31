import pytest
from unittestzero import Assert
from urlparse import urlparse


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=["test_zone"])
def zone(request, cfme_data):
    param = request.param
    return cfme_data.data['zones'][param]


@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestZone:
    '''Simple set of tests to support creating and assigning appliance zones
    '''
    def test_add_new_zone(self, mozwebqa, configuration_pg, zone, cfme_data):
        '''Add new zone
        '''
        win_domain_data = cfme_data.data['ldap_server']
        smartproxy_ip = urlparse(mozwebqa.base_url).netloc

        zone_pg = configuration_pg.click_on_settings().click_on_zones()\
            .click_on_add_new()
        zone_pg.set_zone_info(
            zone['name'],
            zone['description'],
            smartproxy_ip)
        zone_pg.set_ntp_servers(*zone['ntp_servers'])
        zone_pg.set_windows_credentials(
            win_domain_data['bind_dn'],
            win_domain_data['bind_passwd'])
        zones_pg = zone_pg.save()
        Assert.contains(
            'Zone "%s" was added' % zone['name'],
            zones_pg.flash.message,
            'Flash save message does not match')

    def test_set_zone(self, configuration_pg, zone):
        '''Assign appliance to zone
        '''
        server_pg = configuration_pg.click_on_settings().\
            click_on_current_server_tree_node().click_on_server_tab()
        server_pg.set_zone(zone['name'])
        server_pg = server_pg.save()
        Assert.contains(
            'Configuration settings saved for EVM Server',
            server_pg.flash.message,
            'Flash save message does not match')
