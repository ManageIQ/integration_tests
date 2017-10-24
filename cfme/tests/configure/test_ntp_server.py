from functools import partial

from cfme import test_requirements
from datetime import datetime, timedelta
from cfme.utils.browser import quit
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
import fauxfactory
import pytest


pytestmark = [test_requirements.configuration]


@pytest.fixture
def ntp_servers_keys(appliance):
    return appliance.server.settings.ntp_servers_fields_keys


@pytest.fixture
def empty_ntp_dict(ntp_servers_keys):
    return dict.fromkeys(ntp_servers_keys, '')


def appliance_date(appliance):
    status, msg = appliance.ssh_client.run_command("date --iso-8601=hours")
    return datetime.strptime(msg.rsplit('-', 1)[0], '%Y-%m-%dT%H')


def check_ntp_grep(appliance, clock):
    status, msg = appliance.ssh_client.run_command(
        "cat /etc/chrony.conf| grep {}".format(clock))
    return not bool(status)


def clear_ntp_settings(appliance, empty_ntp_dict):
    ntp_file_date_stamp = appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    appliance.server.settings.update_ntp_servers(empty_ntp_dict)
    wait_for(lambda: ntp_file_date_stamp != appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)


@pytest.mark.tier(2)
def test_ntp_crud(request, appliance, empty_ntp_dict, ntp_servers_keys):
    # Adding finalizer
    request.addfinalizer(lambda: appliance.server.settings.update_ntp_servers(empty_ntp_dict))
    """ Insert, Update and Delete the NTP servers """
    # set from yaml file
    appliance.server.settings.update_ntp_servers(dict(zip(
        ntp_servers_keys, [ntp_server for ntp_server in cfme_data['clock_servers']])))
    # Set from random values
    appliance.server.settings.update_ntp_servers(dict(zip(
        ntp_servers_keys, [fauxfactory.gen_alphanumeric() for _ in range(3)])))
    # Deleting the ntp values
    appliance.server.settings.update_ntp_servers(empty_ntp_dict)


@pytest.mark.tier(3)
def test_ntp_server_max_character(request, appliance, ntp_servers_keys, empty_ntp_dict):
    request.addfinalizer(partial(clear_ntp_settings, appliance, empty_ntp_dict))
    ntp_file_date_stamp = appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    appliance.server.settings.update_ntp_servers(dict(zip(
        ntp_servers_keys, [fauxfactory.gen_alphanumeric() for _ in range(3)])))
    wait_for(lambda: ntp_file_date_stamp != appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)


@pytest.mark.tier(3)
def test_ntp_conf_file_update_check(request, appliance, empty_ntp_dict, ntp_servers_keys):

    request.addfinalizer(lambda: appliance.server.settings.update_ntp_servers(empty_ntp_dict))
    ntp_file_date_stamp = appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    # Adding the ntp server values
    appliance.server.settings.update_ntp_servers(dict(zip(
        ntp_servers_keys, [ntp_server for ntp_server in cfme_data['clock_servers']])))
    wait_for(lambda: ntp_file_date_stamp != appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)
    for clock in cfme_data['clock_servers']:
        status, wait_time = wait_for(lambda: check_ntp_grep(appliance, clock),
            fail_condition=False, num_sec=60, delay=5)
        assert status is True, "Clock value {} not update in /etc/chrony.conf file".format(clock)

    # Unsetting the ntp server values
    ntp_file_date_stamp = appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    appliance.server.settings.update_ntp_servers(empty_ntp_dict)
    wait_for(lambda: ntp_file_date_stamp != appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)
    for clock in cfme_data['clock_servers']:
        status, wait_time = wait_for(lambda: check_ntp_grep(appliance, clock),
            fail_condition=True, num_sec=60, delay=5)
        assert status is False, "Found clock record '{}' in /etc/chrony.conf file".format(clock)


@pytest.mark.tier(3)
def test_ntp_server_check(request, appliance, ntp_servers_keys):
    request.addfinalizer(lambda: appliance.server.settings.update_ntp_servers(empty_ntp_dict))
    orig_date = appliance_date(appliance)
    past_date = orig_date - timedelta(days=10)
    logger.info("dates: orig_date - %s, past_date - %s", orig_date, past_date)
    status, result = appliance.ssh_client.run_command(
        "date +%Y%m%d -s \"{}\"".format(past_date.strftime('%Y%m%d')))
    new_date = appliance_date(appliance)
    if new_date != orig_date:
        logger.info("Successfully modified the date in the appliance")
        # Configuring the ntp server and restarting the appliance
        # checking if ntp property is available, adding if it is not available
        appliance.server.settings.update_ntp_servers(dict(zip(
            ntp_servers_keys, [ntp_server for ntp_server in cfme_data['clock_servers']])))
        yaml_config = appliance.get_yaml_config()
        ntp = yaml_config.get("ntp")
        if not ntp:
            yaml_config["ntp"] = {}
        # adding the ntp interval to 1 minute and updating the configuration
        yaml_config["ntp"]["interval"] = '1.minutes'
        appliance.set_yaml_config(yaml_config)
        # restarting the evmserverd for NTP to work
        appliance.restart_evm_service(rude=True)
        appliance.wait_for_web_ui(timeout=1200)
        # Incase if ntpd service is stopped
        appliance.ssh_client.run_command("service chronyd restart")
        # Providing two hour runtime for the test run to avoid day changing problem
        # (in case if the is triggerred in the midnight)
        wait_for(
            lambda: (orig_date - appliance_date(appliance)).total_seconds() <= 7200, num_sec=300)
    else:
        raise Exception("Failed modifying the system date")
    # Calling the browser quit() method to compensate the session after the evm service restart
    quit()


@pytest.mark.tier(3)
def test_clear_ntp_settings(request, appliance, empty_ntp_dict):
    request.addfinalizer(lambda: appliance.server.settings.update_ntp_servers(empty_ntp_dict))
