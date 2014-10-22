from cfme.configure import configuration
from cfme.fixtures import pytest_selenium as sel
from utils.appliance import IPAppliance
from utils import conf
from utils.conf import cfme_data
from utils.db import get_yaml_config, set_yaml_config
from utils.log import logger
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from urlparse import urlparse

import cfme.web_ui.flash as flash
import pytest


def ssh_command_execution(command):
    with SSHClient() as ssh:
        status, msg = ssh.run_command("%s" % command)
        if status == 0:
            return msg
        else:
            raise Exception("Unable to execute the command")


def configure_ntp_servers(*server_details):
    configuration.unset_ntp_servers()

    if server_details:
        configuration.set_ntp_servers(*server_details)
    else:
        configuration.set_ntp_servers(*cfme_data['clock_servers'])
    flash.assert_message_match(
        "Configuration settings saved for CFME Server \"EVM-CFME [1]\" in Zone \"default\"")


def test_ntp_crud():
    """ Insert, Update and Delete the NTP servers """
    configure_ntp_servers()

    configure_ntp_servers(
        generate_random_string(size=7),
        generate_random_string(size=7),
        generate_random_string(size=7))

    configuration.unset_ntp_servers()


def test_ntp_server_max_character():
    configure_ntp_servers(
        generate_random_string(size=255),
        generate_random_string(size=255),
        generate_random_string(size=255))


def test_ntp_conf_file_update_Check():
    configure_ntp_servers()
    for clock in cfme_data['clock_servers']:
        clock_entry = ssh_command_execution("cat /etc/ntp.conf | grep %s" % clock)
        if clock_entry is None:
            logger.info("NTP server is added in /etc/ntp.conf file")
        else:
            raise Exception("NTP server is not added /etc/ntp.conf file")


def app_address():
    url = urlparse(conf.env['base_url'])
    return url.netloc


def test_ntp_server_check():
        """ Check for the NTP functionality """
        current_date = ssh_command_execution("date +%d")
        previous_date = ssh_command_execution("date --date='10 days ago' +%d")
        modified_date = ssh_command_execution(
            "date --set=\"$(date +'%%y%%m%s %%H:%%M')\"" % previous_date)
        if modified_date != current_date:
            logger.info("Successfully modified the date in the appliance")
            configure_ntp_servers()
            """ Adding the ntp time interval into vmdb and Restarting the evmserverd service """
            app_url = app_address()
            yaml = get_yaml_config("vmdb")
            yaml["ntp"]["interval"] = '1.minute'
            set_yaml_config("vmdb", yaml)
            app = IPAppliance(app_url)
            app.restart_evm_service()
            app.wait_for_web_ui()
            """
            Need to add the wait for logic, which retrives the latest_date and compares with
            current_date. If not synced then wait for few seconds and then execute the above
            proceedure.  Raise time out exception after 3 min or so.
            If synced then exit with results passed
            """
            latest_date = ssh_command_execution("date +%d")
            if latest_date == current_date:
                logger.info("Ntp service is working properly")
            else:
                raise Exception("Ntp service not working")
        else:
            raise Exception("Unable to modify the date")


@pytest.mark.xfail(message='https://bugzilla.redhat.com/show_bug.cgi?id=1153633')
def test_clear_ntp_settings():
    configuration.unset_ntp_servers()
    flash.assert_message_match(
        "Configuration settings saved for CFME Server \"EVM-CFME [1]\" in Zone \"default\"")

    sel.force_navigate("cfg_settings_currentserver_server")
    value1 = sel.value(configuration.ntp_servers.ntp_server_1)
    value2 = sel.value(configuration.ntp_servers.ntp_server_2)
    value3 = sel.value(configuration.ntp_servers.ntp_server_3)
    if value1 is None and value2 is None and value3 is None:
        logger.info("NTP value is cleared")
    else:
        raise Exception("NTP value is not cleared")
