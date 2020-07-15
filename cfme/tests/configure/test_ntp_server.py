from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.configuration, pytest.mark.rhel_testing]

STAT_CMD = "stat --format '%y' /etc/chrony.conf"


@pytest.fixture
def ntp_server_keys(appliance):
    """Return list of NTP server keys (widget attribute names) from ServerInformationView"""
    return appliance.server.settings.ntp_servers_fields_keys


@pytest.fixture
def empty_ntp(ntp_server_keys):
    """Return dictionary of NTP server keys with blank values"""
    return dict.fromkeys(ntp_server_keys, '')


@pytest.fixture
def random_ntp(ntp_server_keys):
    """Return dictionary of NTP server keys with random alphanumeric values"""
    return dict(zip(ntp_server_keys, [fauxfactory.gen_alphanumeric() for _ in range(3)]))


@pytest.fixture
def random_max_ntp(ntp_server_keys):
    """Return dictionary of NTP server keys with random alphanumeric values of max length"""
    return dict(zip(ntp_server_keys, [fauxfactory.gen_alphanumeric(255) for _ in range(3)]))


@pytest.fixture
def config_ntp(ntp_server_keys):
    """Return dictionary of NTP server keys with server names from config yaml"""
    return dict(zip(ntp_server_keys, cfme_data['clock_servers']))


def appliance_date(appliance):
    """Return appliance server datetime, in ISO-8601 format"""
    result = appliance.ssh_client.run_command("date --iso-8601")
    return datetime.fromisoformat(result.output.rstrip())


def chrony_servers(appliance):
    """Return list of the NTP servers from /etc/chrony.conf"""
    servers = appliance.ssh_client.run_command(f"grep ^server /etc/chrony.conf").output
    return [s.split()[1] for s in servers.splitlines()]


def clear_ntp_settings(appliance, empty_ntp):
    """Clear all NTP servers in the UI"""
    last_updated = appliance.ssh_client.run_command(STAT_CMD).output
    appliance.server.settings.update_ntp_servers(empty_ntp)
    wait_for(lambda: last_updated != appliance.ssh_client.run_command(STAT_CMD).output,
        num_sec=60, delay=10)


def update_check_ntp(appliance, ntp_fill):
    """Update NTP servers in the UI, then verify that the changes are reflected in
    /etc/chrony.conf.

    Args:
        appliance: appliance to update
        ntp_fill: :py:class:`dict` of servers to add to UI
    """
    appliance.server.settings.update_ntp_servers(ntp_fill)

    # Check that config file has been updated. Defaults to zone-level NTP settings if server-level
    # values were blank.
    expected_servers = [s for s in ntp_fill.values() if s != '']
    if not expected_servers:
        expected_servers = appliance.server.zone.advanced_settings['ntp']['server']
    wait_for(lambda: chrony_servers(appliance) == expected_servers, num_sec=60, delay=10)


@pytest.mark.tier(2)
def test_ntp_crud(request, appliance, random_ntp, empty_ntp, config_ntp):
    """Update and delete NTP servers in the Server Configuration page, and verify that they are
    updated in /etc/chrony.conf. Finally, restore the NTP servers to the yaml config values.

    TODO: Implement zone- and region-level NTP settings.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/12h
    """
    request.addfinalizer(lambda: update_check_ntp(appliance, config_ntp))

    # Set NTP servers from random values
    update_check_ntp(appliance, random_ntp)

    # Update NTP servers from config
    update_check_ntp(appliance, config_ntp)

    # Delete NTP servers
    update_check_ntp(appliance, empty_ntp)


@pytest.mark.tier(3)
def test_ntp_server_max_character(request, appliance, random_max_ntp, config_ntp):
    """Update NTP servers in UI with 255 char hostname values, and verify that they are added to
    /etc/chrony.conf, then restore the NTP servers to the yaml config values.

    TODO: Implement zone- and region-level NTP settings.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/8h
    """
    request.addfinalizer(lambda: update_check_ntp(appliance, config_ntp))
    update_check_ntp(appliance, random_max_ntp)


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1832278])
def test_ntp_server_check(appliance):
    """Modify server date, and verify that the configured NTP servers restore it.

    TODO: Implement zone- and region-level NTP settings.

    Bugzilla:
        1832278

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Configuration
    """
    orig_date = appliance_date(appliance)
    past_date = orig_date - timedelta(days=1)
    logger.info(f"Server dates: original {orig_date}, new {past_date}.")

    appliance.ssh_client.run_command("systemctl restart chronyd")

    appliance.ssh_client.run_command(f"date --iso-8601 -s '{past_date.isoformat()}'")
    assert appliance_date(appliance) == past_date, "Failed to modify appliance date."
    logger.info("Successfully modified the date in the appliance.")

    wait_for(
        lambda: abs((appliance_date(appliance) - orig_date).total_seconds()) <= 3600, delay=10,
        num_sec=300)
