# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.ignore_stream('upstream'), pytest.mark.manual]


@test_requirements.configuration
def test_can_only_select_this_regions_zones_when_changing_server_zone():
    """
    Bug 1470283 - zones of sub region show up as zones appliances of a
    central region can move to

    Bugzilla:
        1470283

    Configure 1 appliance for use as a reporting db server, with region
    99. Create zones zone-99-a and zone-99-b.
    Configure a 2nd appliance as a remote appliance, with region 0. Create
    zones zone-0-a and zone-0-b.
    In the web UI of the 1st appliance, change the zone of the appliance.
    Verify that only the zones for this appliance"s region (i.e.,
    zone-99-a and zone-99-b) appear in the drop-down list.
    1.) Set up first appliance:
    a.) Request appliance that isn"t pre-configured.
    b.) ssh to appliance and run appliance_console.
    c.) Choose:
    > Configure Database
    > Create key
    > Create Internal Database
    Should this appliance run as a standalone database server?    ? (Y/N):
    |N|
    Enter the database region number: 99
    Enter the database password on 127.0.0.1: smartvm
    d.) Log in to the web UI and enable only the following Server Roles:
    Reporting
    Scheduler
    User Interface
    Web Services
    e.) Create two more zones: tpapaioa-99-a and tpapaioa-99-b
    2.) set up second appliance:
    a.) request appliance that is pre-configured.
    b.) Log in to the web UI and enable replication:
    Administrator > Configuration > Settings > Region 0 > Replication >
    Type: Remote > Save
    3.) on the first appliance:
    a.) set up replication for the second appliance:
    Administrator > Configuration > Settings > Region 99 > Replication >
    Type: Global > Add Subscription >
    Database    vmdb_production
    Host        <ip address of 2nd appliance>
    Username    root
    Password    smartvm
    Port        5432
    > Accept > Save
    4.) on the second appliance, create two more zones: tpapaioa-0-a and
    tpapaioa-0-b.
    5.) on the first appliance, click on the appliance"s Zone drop-down
    menu, and verify that only tpapaioa-99-a and tpapaioa-99-b are
    visible:
    Administrator > Configuration > Server > Zone

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass
