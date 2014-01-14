'''
Created on Jun 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
from unittestzero import Assert
from utils.wait import wait_for
from utils.ipmi import IPMI


@pytest.fixture(params=['esx'])
def single_host_data(request, cfme_data):
    pytest.skip('Test disabled until a proper host is provisioned.')
    return cfme_data['management_hosts'][request.param]


@pytest.fixture(params=[('title', 'Add this Infrastructure Provider'),
        ('alt', 'Add this Infrastructure Provider')])
def attribute_and_value(request):
    '''Returns a tuple containing items to test'''
    return request.param


@pytest.fixture
def provider_add_pg(infra_providers_pg):
    '''Navigate to Infrastructure -> Providers -> Add'''
    return infra_providers_pg.click_on_add_new_provider()


class TestManagementSystemsPages:
    @pytest.mark.nondestructive
    class TestManagementSystemsAddPage:
        def test_that_checks_add_button_attribute(
                self,
                provider_add_pg,
                attribute_and_value):
            attr = attribute_and_value[0]
            expected_value = attribute_and_value[1]

            add_attr = provider_add_pg.add_button.get_attribute(attr)
            Assert.equal(add_attr, expected_value,
                    "Could not verify %s" % expected_value)


def test_host_add(single_host_data, infra_hosts_pg):
    add_pg = infra_hosts_pg.click_add_new_host()
    add_pg.ipmi_button.click()
    add_pg.add_host(single_host_data)
    infra_pg = add_pg.click_on_add()
    Assert.equal(infra_pg.flash.message,
                 "Host \"%s\" was added" % single_host_data['name'],
                 "Flash message should report host added successfully")
    wait_for(lambda host: infra_hosts_pg.check_host_and_refresh(host),
             [single_host_data['name']])


def test_host_power_controls_reset(single_host_data, infra_hosts_pg):
    credentials = infra_hosts_pg.testsetup.credentials[single_host_data['ipmi_credentials']]
    ipmi_host = IPMI(hostname=single_host_data['ipmi_address'],
                     username=credentials['username'],
                     password=credentials['password'])
    ipmi_host.power_off()
    infra_hosts_pg.reset_host(single_host_data['name'])
    Assert.equal(infra_hosts_pg.flash.message,
                 "\"%s\": Reset successfully initiated" % single_host_data['name'],
                 "Flash message should name host as being reset")
    wait_for(ipmi_host.is_power_on,
             handle_exception=True)


def test_host_power_controls_on(single_host_data, infra_hosts_pg):
    credentials = infra_hosts_pg.testsetup.credentials[single_host_data['ipmi_credentials']]
    ipmi_host = IPMI(hostname=single_host_data['ipmi_address'],
                     username=credentials['username'],
                     password=credentials['password'])
    ipmi_host.power_off()
    infra_hosts_pg.flash.click()
    infra_hosts_pg.power_on_host(single_host_data['name'])
    Assert.equal(infra_hosts_pg.flash.message,
                 "\"%s\": Power On successfully initiated" % single_host_data['name'],
                 "Flash message should name host as being Powered On")
    wait_for(ipmi_host.is_power_on,
             handle_exception=True)


def test_host_delete(single_host_data, infra_hosts_pg):
    infra_hosts_pg.select_host(single_host_data['name'])
    infra_hosts_pg.click_remove_host()
    Assert.equal(infra_hosts_pg.flash.message,
                 "Delete initiated for 1 Host from the CFME Database",
                 "Flash message should report host to be deleted")
    wait_for(lambda host: not infra_hosts_pg.check_host_and_refresh(host),
             [single_host_data['name']])
