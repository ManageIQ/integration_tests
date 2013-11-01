# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert
import time

#After initializing the registration process, there has to be a wait
SECONDS_TO_WAIT_FOR_REGISTRATION = 100

@pytest.mark.usefixtures("maximized")
def test_edit_registration_rhn(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    update_method = cfme_data.data['redhat_updates']['registration_method']
    updates_data = cfme_data.data['redhat_updates'][update_method]
    creds_data = updates_pg.testsetup.credentials[
        updates_data["credentials"]]

    #passw = creds_data["password"]
    #Assert.true(1==2, passw)

    if "organization" in updates_data:
        registered_pg = updates_pg.edit_registration_and_save(
            updates_data["url"], creds_data, update_method,
            organization=updates_data["organization"])
    else:
        registered_pg = updates_pg.edit_registration_and_save(
            updates_data["url"], creds_data, update_method, default=True)
    flash_message = "Customer Information successfully saved"
    Assert.equal(registered_pg.flash.message, flash_message,
        registered_pg.flash.message)

@pytest.mark.usefixtures("maximized")
def test_register_appliances(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliances_to_update = cfme_data.data['redhat_updates']['appliances_to_update']
    #updates_pg.register_appliances(appliances_to_update)
    updates_pg.register_appliances()
    flash_message = "Registration has been initiated for the selected Servers"
    Assert.equal(updates_pg.flash.message, flash_message, updates_pg.flash.message)
    waiting_period = SECONDS_TO_WAIT_FOR_REGISTRATION/5
    for count in range(0, waiting_period):
        time.sleep(5)
        #if updates_pg.is_registered(appliances_to_update):
        if updates_pg.is_registered():
            break
        updates_pg.refresh_list()
    if count == (waiting_period - 1):
        pytest.fail("Appliance was unable to register properly")

#Skipped. Appliance is not updating itself yet
@pytest.mark.skipif("True")
@pytest.mark.usefixtures("maximized")
def test_compare_versions_before_update(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliance_versions = cfme_data.data["redhat_updates"]["appliances"]
    Assert.true(updates_pg.are_old_versions_before_update(
        appliance_versions))

#After this test we will probably want to insert some waiting
#Cannot do it now, in the present time the updates are not working
@pytest.mark.usefixtures("maximized")
def test_initiate_updates(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliances_to_update = cfme_data.data['redhat_updates']['appliances_to_update']
    updates_pg.apply_updates(appliances_to_update)
    flash_message = "Update has been initiated for the selected Servers"
    Assert.equal(updates_pg.flash.message, flash_message, updates_pg.flash.message)

#Skipped. Appliance is not updating itself yet
@pytest.mark.skipif("True")
@pytest.mark.usefixtures("maximized")
def test_compare_versions_after_update(cnf_configuration_pg, cfme_data):
    updates_pg = cnf_configuration_pg.click_on_redhat_updates()
    appliance_current_version = cfme_data.data["redhat_updates"]["current_version"]
    Assert.true(updates_pg.is_current_version_after_update(
        appliance_current_version))

@pytest.mark.skip_selenium
def test_certificates_exist(cfme_data, ssh_client):
    cert_list = cfme_data.data["redhat_updates"]["certificates"]
    for cert in cert_list:
        exit_status, output = ssh_client.run_command('ls %s' % cert)
        Assert.true(exit_status == 0, "Certificate '%s' not found" % cert)

