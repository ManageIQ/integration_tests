# -*- coding: utf-8 -*-
# Manual tests for log depot
import pytest

from cfme import test_requirements

pytestmark = [test_requirements.log_depot, pytest.mark.manual]


@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect current log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_all_zone_zone_multiple_servers_server_setup():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone should not be setup,
    servers should

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_current_zone_multiple_servers():
    """
    using any type of depot check collect current log function under zone,
    zone has multiplie servers under it. Zone and all servers should have
    theire own settings

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_collect_all_zone_multiple_servers():
    """
    using any type of depot check collect all log function under zone.
    Zone should have multiplie servers under it. Zone and all servers
    should have their own settings

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_log_multiple_servers_unconfigured():
    """
    Verify that buttons are unclickable (grayed) when log collection
    unconfigured in all servers under one zone

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1.Configure two appliances to work under one zone
              (distribution mode, one master, another slave)
            2. Open appliance"s WebUi -> Settings -> Configuration
            3. Go to Diagnostics tab -> Collect logs
            4. Select second server (slave) and press "collect" select bar
    """
    pass
