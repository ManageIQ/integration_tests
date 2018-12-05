# -*- coding: utf-8 -*-
import pytest

from cfme.configure import about
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_server_name(request, appliance):
    """Tests that changing the server name updates the about page

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/15h
    """

    view = navigate_to(appliance.server, 'Details')
    old_server_name = view.server.basic_information.appliance_name.read()

    @request.addfinalizer
    def _ensure_name_reset():
        appliance.server.settings.update_basic_information({'appliance_name': old_server_name})

    new_server_name = "{}-TEST".format(old_server_name)
    appliance.server.settings.update_basic_information({'appliance_name': new_server_name})
    flash_message = (
        'Configuration settings saved for {} Server "{} [{}]" in Zone "{}"'.format(
            appliance.product_name,
            appliance.server.name,
            appliance.server.sid,
            appliance.server.zone.name))

    view.flash.assert_message(flash_message)

    # CFME updates about box only after any navigation BZ(1408681) - closed wontfix
    navigate_to(appliance.server, 'Dashboard')

    # opens and closes about modal
    current_server_name = about.get_detail(about.SERVER, server=appliance.server)

    assert new_server_name == current_server_name, (
        "Server name in About section does not match the new name")
