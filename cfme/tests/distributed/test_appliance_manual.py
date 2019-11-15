# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.distributed
]


@pytest.mark.tier(1)
def test_distributed_field_zone_description_special():
    """
    Special Chars in description

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.tier(1)
def test_verify_httpd_only_running_when_roles_require_it():
    """
    Provision preconfigured appliance A.
    Provision non-preconfigured appliance B.
    On appliance A, stop server processes:
    # appliance_console
    > Stop EVM Server Processes > Y
    On appliance B, join to appliance A:
    # appliance_console
    > Configure Database > Fetch key from remote machine
    > enter IP address of appliance A
    > root > smartvm
    > /var/www/miq/vmdb/certs/v2_key
    > Join Region in External Database
    > enter IP address of appliance A
    > 5432 > vmdb_production > root > smartvm
    On appliance A, restart server processes:
    > Start EVM Server Processes > Y
    Log in the web UI on appliance A, and disable roles on appliance B
    that require httpd:
    Administrator > Configuration
    > click on appliance B in accordion menu"s list of servers
    > under Server Control, disable all server roles > Save
    On appliance B, verify that the httpd service stops:
    # systemctl status httpd
    ● httpd.service - The Apache HTTP Server
    Loaded: loaded (/usr/lib/systemd/system/httpd.service; disabled;
    vendor preset: disabled)
    Active: inactive (dead) since Fri 2018-01-12 10:57:29 EST; 22s ago
    [...]
    Enable one of the following roles, and verify that httpd restarts:
    Cockpit, Embedded Ansible, User Interface, Web Services, Websocket

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_processor():
    """
    C & U Data Processor (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


def test_distributed_add_provider_to_remote_zone():
    """
    Adding a provider from the global region to a remote zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


def test_distributed_zone_add_provider_to_nondefault_zone():
    """
    Can a new provider be added the first time to a non default zone.

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_delete_occupied():
    """
    Delete Zone that has appliances in it.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(3)
def test_distributed_migrate_embedded_ansible_role():
    """
    Ansible role failsover/migrates when active service fails

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: critical
        initialEstimate: 1/4h
        setup:
            1. Configure a 2 server installation (same region + zone).
            2. Assign the embedded Ansible role to both servers.
            3. Find the server on which this role is active
               (Configuration > Diagnostics > Zone: <zone name> >
               Servers by Roles).
        testSteps:
            1. Run `systemctl stop evmserverd` on active server.
        expectedResults:
            1. Observe that the role is started on the other server.
    """
    pass


@pytest.mark.tier(1)
def test_distributed_field_zone_name_special():
    """
    When creating a new zone, special characters can be used in the name,
    including leading and trailing characters, and the name displays
    correctly in the web UI after saving.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_mixed_appliance_ip_versions():
    """
    IPv6 and IPv4 appliances

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1h
    """
    pass


@pytest.mark.tier(3)
def test_distributed_delete_offline_worker_appliance():
    """
    Steps to Reproduce:
    have 3 servers .
    Shutdown one server. This become inactive.
    go to WebUI > Configuration > Diagnostics > Select "Zone: Default
    zone" > Select worker > Configuration > Delete

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_reporting():
    """
    Reporting (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_data_collector():
    """
    C & U Data Collector (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_web_services():
    """
    Web Services (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_cu_coordinator_singleton():
    """
    C & U Coordinator (singleton role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_smartstate_analysis():
    """
    SmartState Analysis (multiple)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_field_zone_name_whitespace():
    """
    When creating a new zone, the name can have whitespace, including
    leading and trailing characters. After saving, any leading or trailing
    whitespace is not displayed in the web UI.

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


def test_distributed_zone_in_different_networks():
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        initialEstimate: 1h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_scheduler_singleton():
    """
    Scheduler (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_field_zone_description_leading_whitespace():
    """
    Leading whitespace in description

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/30h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_inventory_singleton():
    """
    Provider Inventory (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_provider_operations():
    """
    Provider Operations (multiple appliances can have this role)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.tier(1)
def test_distributed_zone_failover_notifier_singleton():
    """
    Notifier (singleton)

    Polarion:
        assignee: tpapaioa
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


def test_distributed_diagnostics_servers_view():
    """

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


def test_distributed_zone_mixed_infra():
    """
    Azure,AWS, and local infra

    Polarion:
        assignee: tpapaioa
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass
