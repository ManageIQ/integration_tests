from cfme.configure import configuration
from cfme.fixtures import pytest_selenium as sel
from datetime import datetime
from utils.appliance import IPAppliance
from utils.conf import cfme_data
from utils.db import get_yaml_config, set_yaml_config
from utils.log import logger
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for

import cfme.web_ui.flash as flash
import pytest


def ssh_command_execution(command):
    with SSHClient() as ssh:
        status, msg = ssh.run_command("%s" % command)
        if status == 0:
            return msg
        else:
            raise Exception("Unable to execute the command")


def appliance_date():
    return datetime.strptime(ssh_command_execution("date --iso-8601=hours").rsplit('-', 1)[0],
        '%Y-%m-%dT%H')


def configure_ntp_servers(*server_details):
    configuration.unset_ntp_servers()

    if server_details:
        configuration.set_ntp_servers(*server_details)
    else:
        configuration.set_ntp_servers(*cfme_data['clock_servers'])
    flash.assert_message_match(
        "Configuration settings saved for CFME Server \"%s [%s]\" in Zone \"%s\"" % (
            configuration.server_name(),
            configuration.server_id(),
            configuration.server_zone_description().partition(' ')[0].lower()))


def test_ntp_crud():
    """ Insert, Update and Delete the NTP servers """
    # set from yaml file
    configure_ntp_servers()

    # set from random values
    configure_ntp_servers(*(generate_random_string() for _ in range(3)))

    configuration.unset_ntp_servers()


def test_ntp_server_max_character():
    configure_ntp_servers(*(generate_random_string(size=255) for _ in range(3)))


def test_ntp_conf_file_update_Check():
    configure_ntp_servers()
    for clock in cfme_data['clock_servers']:
        clock_entry = ssh_command_execution("cat /etc/ntp.conf | grep %s" % clock).rsplit()
        if clock_entry:
            logger.info("%s is updated in /etc/ntp.conf file successfully" % clock)
        else:
            raise Exception("NTP server %s is not added /etc/ntp.conf file" % clock)


def test_ntp_server_check():
        orig_date = appliance_date()
        past_date = ssh_command_execution("date --date='10 days ago' +%d")
        ssh_command_execution("date --set=\"$(date +'%%y%%m%s %%H:%%M')\"" % past_date)
        prev_date = appliance_date()
        if prev_date != orig_date:
            logger.info("Successfully modified the date in the appliance")
            # Configuring the ntp server and restarting the appliance
            configure_ntp_servers()
            yaml = get_yaml_config("vmdb")
            yaml["ntp"]["interval"] = '1.minute'
            set_yaml_config("vmdb", yaml)
            app = IPAppliance()
            app.restart_evm_service()
            app.wait_for_web_ui()
            # Providing two hour runtime for the test run to avoid day changing problem
            # (in case if the is triggerred in the midnight)
            wait_for(lambda: (orig_date - appliance_date()).total_seconds() <= 7200)
        else:
            raise Exception("Failed modifying the system date")


@pytest.mark.xfail(message='https://bugzilla.redhat.com/show_bug.cgi?id=1153633')
def test_clear_ntp_settings():
    configuration.unset_ntp_servers()
    flash.assert_message_match(
        "Configuration settings saved for CFME Server \"EVM-CFME [1]\" in Zone \"default\"")

    sel.force_navigate("cfg_settings_currentserver_server")
    value1 = sel.value(configuration.ntp_servers.ntp_server_1)
    value2 = sel.value(configuration.ntp_servers.ntp_server_2)
    value3 = sel.value(configuration.ntp_servers.ntp_server_3)
    assert all([value is None for value in (value1, value2, value3)]), "Not all NTP values cleared"
