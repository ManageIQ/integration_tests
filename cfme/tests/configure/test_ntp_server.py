from cfme.configure import configuration
from utils.log import logger
from utils.ssh import SSHClient
from utils.conf import cfme_data
from utils.randomness import generate_random_string


def ssh_command_execution(command):
    with SSHClient() as ssh:
        status, msg = ssh.run_command("%s" % command)
        if status != 0:
            return msg


def configure_ntp_servers():
    configuration.unset_ntp_servers()
    configuration.set_ntp_servers(*cfme_data['clock_servers'])


def test_ntp_crud():
    """ Insert, Update and Delete the NTP servers """
    configure_ntp_servers()

    configuration.set_ntp_servers(
        generate_random_string(size=7),
        generate_random_string(size=7),
        generate_random_string(size=7))

    configuration.unset_ntp_servers()


def test_ntp_server_check():
        """ Check for the NTP functionality """
        current_date = ssh_command_execution("date +%d")
        previous_date = ssh_command_execution("date --date='10 days ago' +%d")
        modified_date = ssh_command_execution(
            "date --set=\"$(date +'%%y%%m%s %%H:%%M')\"" % previous_date)

        if modified_date != current_date:
            logger.info("Successfully modified the date in the appliance")
            configure_ntp_servers()
            """ Need to include the code for modifying the time interval for ntp """
            """ restarting the evmserverd """
            for clock in cfme_data['clock_servers']:
                clock_entry = ssh_command_execution("cat /etc/ntp.con | grep %s" % clock)
                if clock_entry is None:
                    logger.info("NTP server is added")
                else:
                    raise Exception("NTP server is not added")
                ssh_command_execution("service ntpd restart")

                latest_date = ssh_command_execution("date +%d")
                if latest_date == current_date:
                    logger.info("Ntp service is working properly")
                else:
                    raise Exception("Ntp service not working")
        else:
            raise Exception("Unable to modify the date")
