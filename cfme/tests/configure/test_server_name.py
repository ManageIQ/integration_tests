# -*- coding: utf-8 -*-
import pytest

from cfme.configure.about import get_detail
from cfme.configure.configuration import BasicInformation
from cfme.fixtures import pytest_selenium as sel
from fixtures.pytest_store import store
from cfme.web_ui import flash
from utils import clear_property_cache, version
from utils.appliance.implementations.ui import navigate_to


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_server_name(appliance):
    """Tests that changing the server name updates the about page"""
    flash_msg = 'Configuration settings saved for CFME Server "{}'

    navigate_to(appliance.server, 'Server')
    old_server_name = sel.value(BasicInformation.basic_information.appliance_name)

    new_server_name = old_server_name + "-CFME"
    settings_pg = BasicInformation(appliance_name=new_server_name)
    settings_pg.update()
    flash.assert_message_contain(flash_msg.format(new_server_name))
    appliance.server.name = new_server_name
    # CFME updates about box only after any navigation BZ(1408681)
    navigate_to(appliance.server, 'Dashboard')

    current_server_name = get_detail('Server Name')
    if version.current_version() >= '5.7':
        # New modal
        sel.click('//div[contains(@class, "about-modal-pf")]//button[@class="close"]')

    assert new_server_name == current_server_name, \
        "Server name in About section does not match the new name"

    clear_property_cache(store.current_appliance, 'configuration_details')

    settings_pg = BasicInformation(appliance_name=old_server_name)
    settings_pg.update()
    flash.assert_message_contain(flash_msg.format(old_server_name))
    appliance.server.name = old_server_name

    clear_property_cache(store.current_appliance, 'configuration_details')
