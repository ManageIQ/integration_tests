import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.configuration, pytest.mark.long_running]


@pytest.mark.meta(automates=[1536524])
def test_remote_server_advanced_config(distributed_appliances, request):
    """
    Verify that it is possible to navigate to and modify advanced settings for another server from
    the web UI in a distributed appliance configuration.

    Bugzilla:
        1536524

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    primary_appliance, secondary_appliance = distributed_appliances
    secondary_server = primary_appliance.server.secondary_servers[0]

    primary_appliance.browser_steal = True
    with primary_appliance:
        # Advanced tab exists for secondary server
        navigate_to(secondary_server, 'Advanced')

        # Modify a setting for the secondary server
        initial_conf = secondary_server.advanced_settings['server']['startup_timeout']
        secondary_server.update_advanced_settings({'server': {'startup_timeout': initial_conf * 2}})

        new_conf = secondary_server.advanced_settings['server']['startup_timeout']
        assert new_conf == initial_conf * 2
