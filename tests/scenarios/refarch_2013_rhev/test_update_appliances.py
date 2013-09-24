# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.usefixtures("maximized")
class TestUpdateAppliances:
    def test_register_rhn(self, cnf_configuration_pg, cfme_data):
        updates_pg = cnf_configuration_pg.click_on_redhat_updates()
        if updates_pg.is_registered == False:
            update_method = cfme_data.data['redhat_updates']['registration_method']
            updates_data = cfme_data.data['redhat_updates'][update_method]
            creds_data = cnf_configuration_pg.testsetup.credentials[
                    updates_data["credentials"]]
            proxy_data = cfme_data.data["redhat_updates"]["http_proxy"]
            registered_pg = updates_pg.edit_registration_and_save(
                    updates_data["url"], creds_data, update_method, proxy_data)
            flash_message = "Customer Information successfully saved"
            Assert.equal(registered_pg.flash.message, flash_message,
                    registered_pg.flash.message)

    def test_compare_versions_before_update(self, cnf_configuration_pg, cfme_data):
        updates_pg = cnf_configuration_pg.click_on_redhat_updates()
        appliance_versions = cfme_data.data["redhat_updates"]["appliances"]
        Assert.true(updates_pg.are_old_versions_before_update(
                appliance_versions))

    #After this test we will probably want to insert some waiting
    #Cannot do it now, in the present time the updates are not working
    def test_initiate_updates(self, cnf_configuration_pg, cfme_data):
        updates_pg = cnf_configuration_pg.click_on_redhat_updates()
        appliances_to_update = cfme_data.data['redhat_updates']['appliances_to_update']
        updates_pg.apply_updates(appliances_to_update)
        flash_message = "Update has been initiated for the selected Servers"
        Assert.equal(updates_pg.flash.message, flash_message, updates_pg.flash.message)

    def test_compare_versions_after_update(self, cnf_configuration_pg, cfme_data):
        updates_pg = cnf_configuration_pg.click_on_redhat_updates()
        appliance_current_version = cfme_data.data["redhat_updates"]["current_version"]
        Assert.true(updates_pg.is_current_version_after_update(
                appliance_current_version))
