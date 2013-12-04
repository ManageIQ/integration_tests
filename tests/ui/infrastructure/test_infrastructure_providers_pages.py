'''
Created on Jun 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
import pytest
from unittestzero import Assert
from utils.wait import wait_for

@pytest.fixture(params=['esx'])
def single_host_data(request, cfme_data):
    return cfme_data.data['management_hosts'][request.param]


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


def test_host_add(infra_hosts_pg, single_host_data):
    add_pg = infra_hosts_pg.click_add_new_host()
    add_pg.ipmi_button.click()
    add_pg.add_host(single_host_data)
    infra_pg = add_pg.click_on_add()
    Assert.equal(infra_pg.flash.message,
                 "Host \"%s\" was added" % single_host_data['name'],
                 "Flash message should report host added successfully")


def test_host_delete(infra_hosts_pg, single_host_data):
    infra_hosts_pg.select_host(single_host_data['name'])
    infra_hosts_pg.click_remove_host()
    Assert.equal(infra_hosts_pg.flash.message,
                 "Delete initiated for 1 Host from the CFME Database",
                 "Flash message should report host to be deleted")
    wait_for(lambda host: not infra_hosts_pg.check_host_and_refresh(host),
             [single_host_data['name']])
