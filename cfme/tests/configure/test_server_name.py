# -*- coding: utf-8 -*-
import pytest

from cfme.configure import about
from cfme.configure.configuration import BasicInformation
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import flash
from cfme.utils import clear_property_cache
from cfme.utils.appliance.implementations.ui import navigate_to


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
    # CFME updates about box only after any navigation BZ(1408681) - closed wontfix
    navigate_to(appliance.server, 'Dashboard')

    # opens and closes about modal
    current_server_name = about.get_detail(about.SERVER)

    assert new_server_name == current_server_name, \
        "Server name in About section does not match the new name"

    clear_property_cache(appliance, 'configuration_details')

    settings_pg = BasicInformation(appliance_name=old_server_name)
    settings_pg.update()
    flash.assert_message_contain(flash_msg.format(old_server_name))
    appliance.server.name = old_server_name

    clear_property_cache(appliance, 'configuration_details')
