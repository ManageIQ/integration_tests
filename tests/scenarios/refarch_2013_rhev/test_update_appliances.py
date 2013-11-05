# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import time
import threading

#After initializing the registration process, there has to be a wait
SECONDS_TO_WAIT_FOR_REGISTRATION = 100
#Check registration every REG_REFRESH seconds
REG_REFRESH = 5
#Wait for update process to complete
SECONDS_TO_WAIT_FOR_UPDATE = 600
#Check update every UP_REFRESH seconds
UP_REFRESH = 20

@pytest.mark.usefixtures("maximized")
def test_edit_registration(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    update_method = cfme_data.data['redhat_updates']['registration_method']
    updates_data = cfme_data.data['redhat_updates'][update_method]
    creds_data = updates_pg.testsetup.credentials[
        updates_data["credentials"]]
    if "organization" in updates_data:
        registered_pg = updates_pg.edit_registration_and_save(
            updates_data["url"], creds_data, update_method,
            organization=updates_data["organization"])
    else:
        registered_pg = updates_pg.edit_registration_and_save(
            updates_data["url"], creds_data, update_method)
    flash_message = "Customer Information successfully saved"
    Assert.equal(registered_pg.flash.message, flash_message,
        registered_pg.flash.message)

#TODO insert some more waiting for the default check for updates
#maybe new test? or include the check in this one
@pytest.mark.usefixtures("maximized")
def test_register_appliances(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliances_to_update = cfme_data.data['redhat_updates']['appliances_to_update']
    updates_pg.register_appliances()
    flash_message = "Registration has been initiated for the selected Servers"
    Assert.equal(updates_pg.flash.message, flash_message, updates_pg.flash.message)
    waiting_interval = SECONDS_TO_WAIT_FOR_REGISTRATION/REG_REFRESH
    for count in range(0, waiting_interval):
        time.sleep(REG_REFRESH)
        if updates_pg.systems_registered():
            break
        updates_pg.refresh_list()
    if count == (waiting_interval - 1):
        pytest.fail("Appliance was unable to register properly")

@pytest.mark.usefixtures("maximized")
def test_versions_before_update(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliance_versions = cfme_data.data["redhat_updates"]["appliances"]
    Assert.true(updates_pg.check_versions(appliance_versions),
        "Version check before update failed. Check your cfme_data.yaml")

#TODO experimental helping function
def login_again(mozwebqa):
    from pages.login import LoginPage
    login_pg = LoginPage(mozwebqa)
    login_pg.go_to_login_page()
    home_pg = login_pg.login()
    cnf_configuration_pg = home_pg.header.site_navigation_menu('Configure')\
        .sub_navigation_menu('Configuration').click()
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()

#Workflow without updating the main appliance. It has to be current already
#TODO update main appliance also
#TODO timeout - we need somehow to detect login screen
#if not updates_pg.is_the_current_page then login again
@pytest.mark.usefixtures("maximized")
def test_update_cfme(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliances_to_update = cfme_data.data['redhat_updates']['appliances_to_update']
    appliance_current_version = cfme_data.data["redhat_updates"]["current_version"]
    updates_pg.apply_updates(appliances_to_update)
    flash_message = "Update has been initiated for the selected Servers"
    Assert.equal(updates_pg.flash.message, flash_message, updates_pg.flash.message)
    waiting_interval = SECONDS_TO_WAIT_FOR_UPDATE/UP_REFRESH
    for count in range(0, waiting_interval):
        time.sleep(UP_REFRESH)
        #TODO check if we need this (run watchdog)
        if not updates_pg.is_the_current_page:
            login_again(mozwebqa)
        if updates_pg.check_versions(appliance_current_version):
            break
        updates_pg.refresh_list()
    if count == (waiting_interval - 1):
        pytest.fail("Timeout while waiting for appliance update")

def test_platform_updates(cnf_configuration_pg, cfme_data, ssh_client):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliances = cfme_data.data['redhat_updates']['appliances']
    for appliance in appliances:
        ssh_client(hostname=appliance['url']).run_command('yum update -y &')
    waiting_interval = SECONDS_TO_WAIT_FOR_UPDATE/UP_REFRESH
    for count in range(0, waiting_interval):
        time.sleep(UP_REFRESH)
        if not updates_pg.platform_updates_available():
            break
        updates_pg.refresh_updates()
    if count == (waiting_interval - 1):
        pytest.fail("Timeout while waiting for platform updates")

@pytest.mark.skip_selenium
def test_certificates_exist(cfme_data, ssh_client):
    cert_list = cfme_data.data["redhat_updates"]["certificates"]
    for cert in cert_list:
        exit_status, output = ssh_client.run_command('ls %s' % cert)
        Assert.true(exit_status == 0, "Certificate '%s' not found" % cert)

