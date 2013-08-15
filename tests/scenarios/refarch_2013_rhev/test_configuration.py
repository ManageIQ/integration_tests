'''
CFME automation to setup reference architecture
See https://access.redhat.com/site/articles/411683
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert
from urlparse import urlparse


pytestmark = [pytest.mark.usefixtures("maximized")]
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'


def test_configure_auth_mode(cnf_configuration_pg, cfme_data):
    '''Configure authentication mode
    '''
    server_data = cfme_data.data['ldap_server']
    auth_pg = cnf_configuration_pg.click_on_settings().\
        click_on_current_server_tree_node().click_on_authentication_tab()
    if auth_pg.current_auth_mode != server_data['mode']:
        auth_pg.ldap_server_fill_data(**server_data)
        if server_data['get_groups'] and server_data['mode'] != "database":
            auth_pg.validate()
            Assert.contains("LDAP Settings validation was successful",
                auth_pg.flash.message,
                FLASH_MESSAGE_NOT_MATCHED)
        auth_pg = auth_pg.save()
        Assert.contains("Authentication settings saved",
            auth_pg.flash.message,
            FLASH_MESSAGE_NOT_MATCHED)


def test_add_new_group(cnf_configuration_pg, user_group):
    '''Add new user group
    '''
    add_new_group_pg = cnf_configuration_pg.click_on_access_control().\
        click_on_groups().click_on_add_new()
    add_new_group_pg.fill_info(user_group['name'], user_group['role'])
    groups_pg = add_new_group_pg.save()
    Assert.contains('Group "%s" was saved' % user_group['name'],
        groups_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_add_new_zone(cnf_configuration_pg, zone, cfme_data):
    '''Add new zone
    '''
    win_domain_data = cfme_data.data['ldap_server']
    smartproxy_ip = urlparse(cnf_configuration_pg.testsetup.base_url).netloc

    zone_pg = cnf_configuration_pg.click_on_settings().click_on_zones()\
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
        FLASH_MESSAGE_NOT_MATCHED)


def test_assign_zone(cnf_configuration_pg, zone):
    '''Assign appliance to zone
    '''
    server_pg = cnf_configuration_pg.click_on_settings().\
        click_on_current_server_tree_node().click_on_server_tab()
    server_pg.set_zone(zone['name'])
    server_pg = server_pg.save()
    Assert.contains(
        'Configuration settings saved',
        server_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_edit_server_roles(cnf_configuration_pg, roles):
    '''Set roles for appliance
    '''
    server_pg = cnf_configuration_pg.click_on_settings().\
        click_on_current_server_tree_node().click_on_server_tab()
    server_pg.set_server_roles(roles)
    server_pg.save()
    Assert.contains(
        'Configuration settings saved',
        server_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


def test_enable_cap_and_util(cnf_configuration_pg):
    '''Enabled capacity and utilization collection for clusters and datastores
    '''
    server_pg = cnf_configuration_pg.click_on_settings().\
        click_on_first_region().click_on_cap_and_util()
    server_pg.check_all_clusters()
    server_pg.check_all_datastores()
    server_pg.click_on_save()
    Assert.contains(
        'Capacity and Utilization Collection settings saved',
        server_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)
