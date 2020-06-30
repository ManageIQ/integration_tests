import re
from contextlib import contextmanager
from typing import Tuple

from miq_version import LOWEST

from cfme.utils.appliance import IPAppliance
from cfme.utils.appliance.console import AP_WELCOME_SCREEN_TIMEOUT
from cfme.utils.log_validator import LogValidator
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for


@contextmanager
def waiting_for_ha_monitor_started(appl, standby_server_ip, timeout):
    if appl.version < '5.10':
        with LogValidator(
                "/var/www/miq/vmdb/config/failover_databases.yml",
                matched_patterns=[standby_server_ip],
                hostname=appl.hostname).waiting(timeout=timeout):
            yield
    else:
        yield
        wait_for(lambda: appl.evm_failover_monitor.running, timeout=300)


def configure_appliances_ha(appliances: Tuple[IPAppliance, IPAppliance, IPAppliance], pwd):
    """Configure HA environment

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '5' setup db, '1' Creates v2_key, '1' selects internal db,
    '1' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '5' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '6' configure db replication, '2' configure node as standby, '2' cluster node
    number set to 2, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, app1_ip standby appliance ip, confirm settings and wait
    to configure finish, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '9' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    """
    apps0, apps1, apps2 = appliances
    app0_ip = apps0.hostname

    # Configure first appliance as dedicated database
    with SSHExpect(apps0) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: 5,
            '5.10': 7,
            '5.11.2.1': 5
        }))  # Configure Database
        interaction.answer(re.escape('Choose the encryption key: |1| '), '1')
        interaction.answer('Choose the database operation: ', '1')
        # On 5.10, rhevm provider:
        #
        #    database disk
        #
        #    1) /dev/sr0: 0 MB
        #    2) /dev/vdb: 4768 MB
        #    3) Don't partition the disk
        if apps0.version < '5.11.2.0':
            interaction.answer(re.escape('Choose the database disk: '),
                            '1' if apps0.version < '5.10' else '2')
        else:
            interaction.answer(re.escape('Choose the database disk: |1| '), '')

        # Should this appliance run as a standalone database server?
        interaction.answer(re.escape('? (Y/N): |N| '), 'y')
        interaction.answer('Enter the database password on localhost: ', pwd)
        interaction.answer('Enter the database password again: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=6 * 60)

        wait_for(lambda: apps0.db.is_dedicated_active, num_sec=4 * 60)

    # Configure EVM webui appliance with create region in dedicated database
    with SSHExpect(apps2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: 5,
            '5.10': 7,
            '5.11.2.1': 5
        }))  # Configure Database
        interaction.answer(re.escape('Choose the encryption key: |1| '), '2')
        interaction.send(app0_ip)
        interaction.answer(re.escape('Enter the appliance SSH login: |root| '), '')
        interaction.answer('Enter the appliance SSH password: ', pwd)
        interaction.answer(
            re.escape('Enter the path of remote encryption key: |/var/www/miq/vmdb/certs/v2_key| '),
            '')
        interaction.answer('Choose the database operation: ', '2', timeout=30)
        interaction.answer('Enter the database region number: ', '0')
        # WARNING: Creating a database region will destroy any existing data and
        # cannot be undone.
        interaction.answer(re.escape('Are you sure you want to continue? (Y/N):'), 'y')
        interaction.answer('Enter the database hostname or IP address: ', app0_ip)
        interaction.answer(re.escape('Enter the port number: |5432| '), '')
        interaction.answer(r'Enter the name of the database on .*: \|vmdb_production\| ', '')
        interaction.answer(re.escape('Enter the username: |root| '), '')
        interaction.answer('Enter the database password on .*: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=360)

    apps2.evmserverd.wait_for_running()
    apps2.wait_for_web_ui()

    apps0.appliance_console.configure_primary_replication_node(pwd)
    apps1.appliance_console.configure_standby_replication_node(pwd, app0_ip)

    configure_automatic_failover(apps2, primary_ip=None)
    return appliances


def configure_automatic_failover(appliance: IPAppliance, primary_ip):
    # Configure automatic failover on EVM appliance
    with SSHExpect(appliance) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
        interaction.expect('Choose the advanced setting: ')

        with waiting_for_ha_monitor_started(appliance, primary_ip, timeout=300):
            # Configure Application Database Failover Monitor
            interaction.send(VersionPicker({
                LOWEST: 8,
                '5.10': 10,
                '5.11.2.1': 8
            }))

            interaction.answer('Choose the failover monitor configuration: ', '1')
            # Failover Monitor Service configured successfully
            interaction.answer('Press any key to continue.', '')
