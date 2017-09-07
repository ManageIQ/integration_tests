# -*- coding: utf-8 -*-
import pytest

from cfme.configure import about
from cfme.utils import clear_property_cache
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_server_name(appliance):
    """Tests that changing the server name updates the about page"""

    view = navigate_to(appliance.server.settings, 'Details')
    old_server_name = view.basic_information.appliance_name.read()
    new_server_name = "{}-CFME".format(old_server_name)
    appliance.server.settings.update_basic_information({'appliance_name': new_server_name})

    # CFME updates about box only after any navigation BZ(1408681) - closed wontfix
    navigate_to(appliance.server, 'Dashboard')

    # opens and closes about modal
    current_server_name = about.get_detail(about.SERVER)

    assert new_server_name == current_server_name, (
        "Server name in About section does not match the new name")

    clear_property_cache(appliance, 'configuration_details')
    appliance.server.settings.update_basic_information({'appliance_name': old_server_name})
    clear_property_cache(appliance, 'configuration_details')
