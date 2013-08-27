# -*- coding: utf-8 -*-

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
@pytest.mark.parametrize("services", [
  "rhsm",
  "sat5",
  "sat6"])
class TestRedhatUpdates:
    def test_redhat_updates(self, cnf_configuration_pg, services):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        updates_pg = cnf_configuration_pg.click_on_redhat_updates()
        creds = dict(
                username='test_username',
                password='test_password')
        cancelled_pg = updates_pg.edit_registration_and_cancel(
                "http://www.testing.url", creds, services)
        flash_message = "Edit of Customer Information was cancelled"
        Assert.equal(cancelled_pg.flash.message, flash_message,
                cancelled_pg.flash.message)
