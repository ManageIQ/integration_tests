"""This module contains REST API specific tests which do not require a provider setup.
For tests that do require provider setup, add them to test_rest.py"""
import pytest

from cfme import test_requirements
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.rest, pytest.mark.tier(1)]


@pytest.fixture
def change_company_name(appliance):
    old_company_name = appliance.advanced_settings["server"]["company"]
    updated_company_name = "REST Company Name"
    appliance.update_advanced_settings({"server": {"company": updated_company_name}})

    yield updated_company_name

    appliance.update_advanced_settings({"server": {"company": old_company_name}})


@pytest.mark.meta(automates=[1596142])
@pytest.mark.customer_scenario
def test_update_roles_via_rest_name_change(appliance, request, change_company_name):
    """
    Bugzilla:
        1596142

    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Change the current server name to something other than the default.
        testSteps:
            1. Send a PATCH request to update the server roles via REST using
                `appliance.update_advanced_settings({"server": {"role": :roles}})`
            2. Check if the server name was set to default.
        expectedResults:
            1. Request was successful.
            2. Server name remains the same.
    """
    old_roles = appliance.advanced_settings["server"]["role"]

    # enable_notifier is set to True, if we need to enable the notifier, else False
    enable_notifier = "notifier" not in old_roles

    # in case the role is already enabled, disable it
    new_roles = f"{old_roles},notifier" if enable_notifier else old_roles.replace("notifier", "")

    appliance.update_advanced_settings({"server": {"role": new_roles}})

    request.addfinalizer(
        lambda: appliance.update_advanced_settings({"server": {"role": old_roles}})
    )

    wait_for(
        lambda: appliance.server_roles["notifier"] == enable_notifier,
        delay=1,
        num_sec=120,
        message="Wait until the role change comes into effect.",
    )
    assert appliance.advanced_settings["server"]["company"] == change_company_name
