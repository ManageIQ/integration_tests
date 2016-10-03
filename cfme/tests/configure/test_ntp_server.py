from cfme import test_requirements
from cfme.configure import configuration
from datetime import datetime, timedelta
from fixtures.pytest_store import store
from utils.browser import quit
from utils.conf import cfme_data
from utils.log import logger
from utils.wait import wait_for
import fauxfactory
import pytest


pytestmark = [test_requirements.configuration]


def appliance_date():
    status, msg = store.current_appliance.ssh_client.run_command("date --iso-8601=hours")
    return datetime.strptime(msg.rsplit('-', 1)[0], '%Y-%m-%dT%H')


def check_ntp_grep(clock):
    status, msg = store.current_appliance.ssh_client.run_command(
        "cat /etc/chrony.conf| grep {}".format(clock))
    return not bool(status)


def clear_ntp_settings():
    ntp_file_date_stamp = store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    configuration.set_ntp_servers()
    wait_for(lambda: ntp_file_date_stamp != store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)


@pytest.mark.tier(2)
def test_ntp_crud(request):
    # Adding finalizer
    request.addfinalizer(configuration.set_ntp_servers)
    """ Insert, Update and Delete the NTP servers """
    # set from yaml file
    configuration.set_ntp_servers(*cfme_data['clock_servers'])
    # Set from random values
    configuration.set_ntp_servers(*(fauxfactory.gen_alphanumeric() for _ in range(3)))
    # Deleting the ntp values
    configuration.set_ntp_servers()


@pytest.mark.tier(3)
def test_ntp_server_max_character(request):
    request.addfinalizer(clear_ntp_settings)
    ntp_file_date_stamp = store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    configuration.set_ntp_servers(*(fauxfactory.gen_alphanumeric(255) for _ in range(3)))
    wait_for(lambda: ntp_file_date_stamp != store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)


@pytest.mark.tier(3)
def test_ntp_conf_file_update_check(request):
    request.addfinalizer(configuration.set_ntp_servers)
    ntp_file_date_stamp = store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    # Adding the ntp server values
    configuration.set_ntp_servers(*cfme_data['clock_servers'])
    wait_for(lambda: ntp_file_date_stamp != store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)
    for clock in cfme_data['clock_servers']:
        status, wait_time = wait_for(lambda: check_ntp_grep(clock),
            fail_condition=False, num_sec=60, delay=5)
        assert status is True, "Clock value {} not update in /etc/chrony.conf file".format(clock)

    # Unsetting the ntp server values
    ntp_file_date_stamp = store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1]
    configuration.set_ntp_servers()
    wait_for(lambda: ntp_file_date_stamp != store.current_appliance.ssh_client.run_command(
        "stat --format '%y' /etc/chrony.conf")[1], num_sec=60, delay=10)
    for clock in cfme_data['clock_servers']:
        status, wait_time = wait_for(lambda: check_ntp_grep(clock),
            fail_condition=True, num_sec=60, delay=5)
        assert status is False, "Found clock record '{}' in /etc/chrony.conf file".format(clock)


@pytest.mark.tier(3)
def test_ntp_server_check(request):
    request.addfinalizer(clear_ntp_settings)
    orig_date = appliance_date()
    past_date = orig_date - timedelta(days=10)
    logger.info("dates: orig_date - %s, past_date - %s", orig_date, past_date)
    status, result = store.current_appliance.ssh_client.run_command(
        "date +%Y%m%d -s \"{}\"".format(past_date.strftime('%Y%m%d')))
    new_date = appliance_date()
    if new_date != orig_date:
        logger.info("Successfully modified the date in the appliance")
        # Configuring the ntp server and restarting the appliance
        # checking if ntp property is available, adding if it is not available
        configuration.set_ntp_servers(*cfme_data['clock_servers'])
        yaml_config = store.current_appliance.get_yaml_config("vmdb")
        ntp = yaml_config.get("ntp", None)
        if not ntp:
            yaml_config["ntp"] = {}
        # adding the ntp interval to 1 minute and updating the configuration
        yaml_config["ntp"]["interval"] = '1.minutes'
        store.current_appliance.set_yaml_config("vmdb", yaml_config)
        # restarting the evmserverd for NTP to work
        store.current_appliance.restart_evm_service(rude=True)
        store.current_appliance.wait_for_web_ui(timeout=1200)
        # Incase if ntpd service is stopped
        store.current_appliance.ssh_client.run_command("service chronyd restart")
        # Providing two hour runtime for the test run to avoid day changing problem
        # (in case if the is triggerred in the midnight)
        wait_for(lambda: (orig_date - appliance_date()).total_seconds() <= 7200, num_sec=300)
    else:
        raise Exception("Failed modifying the system date")
    # Calling the browser quit() method to compensate the session after the evm service restart
    quit()


@pytest.mark.tier(3)
def test_clear_ntp_settings(request):
    request.addfinalizer(configuration.set_ntp_servers)
