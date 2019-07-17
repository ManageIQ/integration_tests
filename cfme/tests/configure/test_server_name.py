# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.configure import about
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [test_requirements.general_ui]


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1635178])
@pytest.mark.sauce
def test_server_name(request, appliance):
    """Tests that changing the server name updates the about page

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """

    view = navigate_to(appliance.server, 'Details')
    old_server_name = view.server.basic_information.appliance_name.read()
    assert old_server_name != ''  # name should at least be set

    @request.addfinalizer
    def _ensure_name_reset():
        appliance.rename(old_server_name)

    new_server_name = "RENAME-TEST"
    assert view.server.basic_information.appliance_name.fill(new_server_name)
    assert view.server.save.is_enabled
    view.server.save.click()  # no boolean return
    assert appliance.server.name == new_server_name

    view.flash.assert_success_message(
        'Configuration settings saved for {} Server "{} [{}]" in Zone "{}"'
        .format(appliance.product_name,
                appliance.server.name,
                appliance.server.sid,
                appliance.server.zone.name)
    )

    # CFME updates about box only after any navigation BZ(1408681) - closed wontfix
    navigate_to(appliance.server, 'Dashboard')

    # opens and closes about modal
    assert new_server_name == about.get_detail(about.SERVER, server=appliance.server), (
        "Server name in About section does not match the new name")
