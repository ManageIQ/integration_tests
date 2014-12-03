from cfme import login
from cfme.configure import configuration
from cfme.fixtures import pytest_selenium as sel
from datetime import datetime
from fixtures.pytest_store import store
from utils.conf import cfme_data
from utils.db import get_yaml_config, set_yaml_config
from utils.log import logger
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for

import pytest


def ssh_command_execution(command):
    with SSHClient() as ssh:
        status, msg = ssh.run_command("%s" % command)
        if status == 0:
            return msg


def appliance_date():
    return datetime.strptime(ssh_command_execution("date --iso-8601=hours").rsplit('-', 1)[0],
        '%Y-%m-%dT%H')


def test_ntp_crud():
    """ Insert, Update and Delete the NTP servers """
    # set from yaml file
    configuration.configure_ntp_servers()

    # set from random values
    configuration.configure_ntp_servers(*(generate_random_string() for _ in range(3)))

    configuration.unset_ntp_servers()


def test_ntp_server_max_character():
    configuration.configure_ntp_servers(*(generate_random_string(size=255) for _ in range(3)))


def test_ntp_conf_file_update_check():
    configuration.configure_ntp_servers()
    for clock in cfme_data['clock_servers']:
        assert ssh_command_execution("cat /etc/ntp.conf | grep %s" % clock).rsplit()


def test_ntp_server_check():
    orig_date = appliance_date()
    past_date = ssh_command_execution("date --date='10 days ago' +%d")
    ssh_command_execution("date --set=\"$(date +'%%y%%m%s %%H:%%M')\"" % past_date)
    prev_date = appliance_date()
    if prev_date != orig_date:
        logger.info("Successfully modified the date in the appliance")
        # Configuring the ntp server and restarting the appliance
        configuration.configure_ntp_servers()
        yaml = get_yaml_config("vmdb")
        ntp = yaml.get("ntp", None)
        if not ntp:
            yaml["ntp"] = {}
        yaml["ntp"]["interval"] = '1.minute'
        set_yaml_config("vmdb", yaml)
        store.current_appliance.restart_evm_service()
        store.current_appliance.wait_for_web_ui(timeout=1500)
        # Providing two hour runtime for the test run to avoid day changing problem
        # (in case if the is triggerred in the midnight)
        wait_for(lambda: (orig_date - appliance_date()).total_seconds() <= 7200)
    else:
        raise Exception("Failed modifying the system date")
    # Calling the logout function to compensate the session after the evm service restart
    login.logout()


@pytest.mark.bugzilla(1153633)
def test_clear_ntp_settings():
    configuration.unset_ntp_servers()
    sel.force_navigate("cfg_settings_currentserver_server")
    vals = [sel.value(getattr(
        configuration.ntp_servers, "ntp_server_{}".format(idx))) == '' for idx in range(1, 4)]
    assert all(vals)
    for clock in cfme_data['clock_servers']:
        result = ssh_command_execution("cat /etc/ntp.conf | grep %s" % clock)
        if result:
            raise Exception("Appliance failed to clear the /etc/ntp.conf entries")
