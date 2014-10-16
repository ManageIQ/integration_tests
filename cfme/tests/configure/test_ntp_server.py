from cfme.configure import configuration
from utils.ssh import SSHClient


def test_ntp_crud():
    configuration.set_ntp_servers(
        '0.fedora.pool.ntp.org',
        '1.fedora.pool.ntp.org',
        '2.fedora.pool.ntp.org')

    configuration.unset_ntp_servers()


def ntp_server_check():
        """ Check for the NTP functionality """

        with SSHClient() as ssh:
            status, current_date = ssh.run_command('date +%d')
            """
            have to execute this command date --set="$(date +'%y%m(current_date -1 ) %H:%M')"
            """
            status, modified_date = ssh.run_command("comand")
            if status != 0:
                status, changed_date = ssh.run_command('date +%d')
                while (changed_date == current_date - 1):
                    print "Succssfully modified the date"
                    configuration.unset_ntp_servers()
                    configuration.set_ntp_servers(
                        '0.fedora.pool.ntp.org',
                        '1.fedora.pool.ntp.org',
                        '2.fedora.pool.ntp.org')

                    status, ntp_changed_date = ssh.run_command('date +%d')
                    if status != 0:
                        while (ntp_changed_date == current_date):
                            print "Success"
