# -*- coding: utf-8 -*-

# pylint: disable=E1101

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
def test_discover_ec2_form(cloud_providers_pg):
    ''' Verify ec2 discovery form fields and cancel '''
    disc_pg = cloud_providers_pg.click_on_discover_providers()
    Assert.equal(disc_pg.form_title, "Amazon Cloud Providers Discovery")
    disc_pg.click_on_start()
    Assert.equal(disc_pg.flash.message, "User ID is required")
    disc_pg.discover_cloud_providers_and_cancel("user", "pass", "pass")
    Assert.true(cloud_providers_pg.is_the_current_page)

@pytest.mark.nondestructive
def test_openstack_amqp_creds(cloud_providers_pg):
    ''' Verify add rhos cloud provider with amqp creds '''
    new_ms_pg = cloud_providers_pg.click_on_add_new_provider()
    new_ms_pg.select_provider_type('OpenStack')
    new_ms_pg.new_provider_fill_data_amqp_creds(
        "mgmt", "host", "127.0.0.1", "user", "pass")
    cloud_providers_pg = new_ms_pg.click_on_cancel()
    Assert.true(cloud_providers_pg.is_the_current_page)

@pytest.mark.nondestructive
def test_openstack_default_creds(cloud_providers_pg):
    ''' Verify add rhos cloud provider with default creds '''
    new_ms_pg = cloud_providers_pg.click_on_add_new_provider()
    new_ms_pg.select_provider_type('OpenStack')
    new_ms_pg.new_provider_fill_data_default_creds(
        "mgmt", "host", "127.0.0.1", "user", "pass")
    cloud_providers_pg = new_ms_pg.click_on_cancel()
    Assert.true(cloud_providers_pg.is_the_current_page)

@pytest.mark.nondestructive
def test_ec2_default_creds(cloud_providers_pg):
    ''' Verify add ec2 cloud provider with default creds '''
    new_ms_pg = cloud_providers_pg.click_on_add_new_provider()
    new_ms_pg.select_provider_type('Amazon EC2')
    new_ms_pg.select_amazon_region()
    new_ms_pg.new_provider_fill_data_default_creds(
        "mgmt", None, None, "user", "pass")
    cloud_providers_pg = new_ms_pg.click_on_cancel()
    Assert.true(cloud_providers_pg.is_the_current_page)
