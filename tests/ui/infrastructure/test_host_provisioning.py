# -*- coding: utf-8 -*-

import pytest
from utils.wait import wait_for
from utils.providers import provider_factory
from utils.ipmi import IPMI
from unittestzero import Assert


@pytest.fixture
def host_provisioning_data(request, cfme_data):
    return cfme_data['provisioning_setup']['host_provisioning_setup']


@pytest.fixture
def setup_host_provisioning_host(infra_hosts_pg, host_provisioning_data):
    if not infra_hosts_pg.check_host_and_refresh(host_provisioning_data['host']['name']):
        add_pg = infra_hosts_pg.click_add_new_host()
        add_pg.add_host(host_provisioning_data['host'])
        add_pg.click_on_add()


def fill_in_request(prov_request_data, provider_data, host_prov_data, tab_buttons):
    request_data = prov_request_data['request']
    request_tab = tab_buttons.tabbutton_by_name("Request").click()
    request_tab.fill_fields(
        request_data['email'],
        request_data['first_name'],
        request_data['last_name'],
        request_data['note'],
        request_data['manager'])

    catalog_data = prov_request_data['catalog']
    catalog_tab = tab_buttons.tabbutton_by_name("Catalog").click()
    catalog_tab.fill_fields(
        catalog_data['pxe_server'],
        catalog_data['image'],
        catalog_data['prov_host'])

    environment_data = prov_request_data['environment']
    cluster_name = "%s / %s" % (environment_data['datacenter'], environment_data['cluster'])
    environment_tab = tab_buttons.tabbutton_by_name("Environment").click()
    environment_tab.fill_fields(
        provider_data['name'],
        cluster_name,
        environment_data['datastores'])

    customize_data = prov_request_data['customize']
    customize_tab = tab_buttons.tabbutton_by_name("Customize").click()
    customize_tab.fill_fields(host_prov_data['pxe_server']['ct_name'],
                              host_prov_data['host']['name'],
                              host_prov_data['host']['ipaddress'],
                              customize_data['subnet_mask'],
                              customize_data['gateway'],
                              customize_data['pw'],
                              customize_data['dns'])

    schedule_data = prov_request_data['schedule']
    schedule_tab = tab_buttons.tabbutton_by_name("Schedule").click()
    schedule_tab.fill_fields(schedule_data['schedule'])


@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures('setup_host_provisioning_pxe')
@pytest.mark.usefixtures('setup_host_provisioning_host')
@pytest.mark.usefixtures('setup_infrastructure_providers')
def test_host_provisioning(infra_hosts_pg, host_provisioning_data, cfme_data, server_roles):

    prov_request_data = host_provisioning_data['provision_request']
    provider_data = cfme_data['management_systems'][prov_request_data['provider']]
    infra_hosts_pg = infra_hosts_pg.header.site_navigation_menu('Infrastructure')\
                                          .sub_navigation_menu('Hosts').click()
    infra_hosts_pg.select_host(host_provisioning_data['host']['name'])
    prov_pg = infra_hosts_pg.click_provision_host()
    tab_buttons = prov_pg.tabbutton_region

    fill_in_request(prov_request_data, provider_data, host_provisioning_data, tab_buttons)
    requests_pg = prov_pg.click_on_submit()

    Assert.equal(requests_pg.flash.message,
                 "Host Request was Submitted, you will be notified when your Hosts are ready",
                 "Flash message should inform of pending notification")
    requests_pg.wait_for_request_status('Last 7 Days', 'Ok', 30)

    infra_hosts_pg = requests_pg.header.site_navigation_menu('Infrastructure')\
                                       .sub_navigation_menu('Hosts').click()
    host_pg = infra_hosts_pg.click_host(host_provisioning_data['host']['name'])
    Assert.equal(host_pg.provider, provider_data['name'],
                 "Provider name does not match")
    Assert.equal(host_pg.cluster, prov_request_data['environment']['cluster'],
                 "Cluster does not match")

    ds_pg = host_pg.click_on_datastores()
    datastores = [ds.title for ds in ds_pg.quadicon_region.quadicons]
    Assert.true(set(prov_request_data['environment']['datastores']).issubset(set(datastores)),
                "Datastores are missing some members")

    mgmt_system = provider_factory(prov_request_data['provider'])
    mgmt_system.remove_host_from_cluster(host_provisioning_data['host']['ipaddress'])

    creds = ds_pg.testsetup.credentials[host_provisioning_data['host']['ipmi_credentials']]
    ipmi = IPMI(host_provisioning_data['host']['ipmi_address'],
                creds['username'], creds['password'], 'lanplus')
    ipmi.power_off()

    infra_hosts_pg = ds_pg.header.site_navigation_menu('Infrastructure')\
                                 .sub_navigation_menu('Hosts').click()
    infra_hosts_pg.select_host(host_provisioning_data['host']['name'])
    infra_hosts_pg.click_remove_host()
    wait_for(lambda func, host: not func(host),
             [infra_hosts_pg.check_host_and_refresh, host_provisioning_data['host']['name']],
             message="wait for host delete")
