import pytest
from paramiko_expect import SSHClientInteraction
from cfme.fixtures.appliance import sprout_appliances
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.fixture(scope="function")
def three_temp_appliances_unconfig_funcscope_rhevm(appliance, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            count=3,
            preconfigured=False,
            provider_type='rhevm'
    ) as appliances:
        yield appliances


def deploy_primary_db(appl_db1):
    interaction = SSHClientInteraction(appl_db1.ssh_client, timeout=5, display=True)
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=20)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('5')
    interaction.expect('Choose the encryption key: |1| ')
    interaction.send('1')
    interaction.expect('Choose the database operation: ')
    interaction.send('1')
    interaction.expect('Choose the database disk:.* ')
    interaction.send('1' if appl_db1.version < '5.10' else '2')
    interaction.expect('\? \(Y/N\): |N| ')
    interaction.send('Y')
    interaction.expect('Enter the database password on localhost: ')
    interaction.send('qwe')
    interaction.expect('Enter the database password again: ')
    interaction.send('qwe')
    interaction.expect('Configuration activated successfully.', timeout=30)
    interaction.expect('Press any key to continue.', timeout=100)


def deploy_evm(appl_evm, appl_db):
    interaction = SSHClientInteraction(appl_evm.ssh_client, timeout=5, display=True)
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=20)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('5')
    interaction.expect('Choose the encryption key: |1|')
    interaction.send('2')
    interaction.expect('Enter the hostname for appliance with encryption key: ')
    interaction.send(appl_db.hostname)
    interaction.expect('Enter the appliance SSH login: |root| ')
    interaction.send('')
    interaction.expect('Enter the appliance SSH password: ')
    interaction.send('smartvm')
    interaction.expect('Enter the path of remote encryption key: |/var/www/miq/vmdb/certs/v2_key|')
    interaction.send('')
    interaction.expect('Choose the database operation: ')
    interaction.send('2')
    interaction.expect('Enter the database region number: ')
    interaction.send('1')
    interaction.expect('Are you sure you want to continue\? \(Y/N\):')
    interaction.send('y')
    interaction.expect('Enter the database hostname or IP address: ')
    interaction.send(appl_db.hostname)
    interaction.expect('Enter the port number: |5432| ')
    interaction.send('')
    interaction.expect('Enter the name of the database on .*: |vmdb_production| ')
    interaction.send('')
    interaction.expect('Enter the username: |root| ')
    interaction.send('')
    interaction.expect('Enter the database password on .*: ')
    interaction.send('qwe')
    interaction.expect('Press any key to continue.', timeout=100)
    interaction.send('')


def configure_db_replication(appl):
    interaction = SSHClientInteraction(appl.ssh_client, timeout=5, display=True)
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=20)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('6')
    interaction.expect('Choose the database replication operation: ')
    interaction.send('1')
    interaction.expect('Enter the number uniquely identifying this node in the replication cluster: ')
    interaction.send('1')
    interaction.expect('Enter the cluster database name: |vmdb_production| ')
    interaction.send('')
    interaction.expect('Enter the cluster database username: |root|')
    interaction.send('')
    interaction.expect('Enter the cluster database password: ')
    interaction.send('qwe')
    interaction.expect('Enter the cluster database password: ')
    interaction.send('qwe')
    interaction.expect('Enter the primary database hostname or IP address: |.*| ')
    interaction.send('')
    interaction.expect('Apply this Replication Server Configuration\? \(Y/N\): ')
    interaction.send('y')
    interaction.expect('Press any key to continue.', timeout=100)
    interaction.send('')


def deploy_standby_db(appl, appl_db1):
    interaction = SSHClientInteraction(appl.ssh_client, timeout=5, display=True)
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=20)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('6')
    interaction.expect('Choose the database replication operation: ')
    interaction.send('2')
    interaction.expect('Choose the encryption key: |1| ')
    interaction.send('2')
    interaction.expect('Enter the hostname for appliance with encryption key: ')
    interaction.send(appl_db1.hostname)
    interaction.expect('Enter the appliance SSH login: |root| ')
    interaction.send('')
    interaction.expect('Enter the appliance SSH password: ')
    interaction.send('smartvm')
    interaction.expect('Enter the path of remote encryption key: |/var/www/miq/vmdb/certs/v2_key|')
    interaction.send('')
    interaction.expect('Choose the standby database disk:.* ')
    interaction.send('1' if appl_db1.version < '5.10' else '2')
    # For some reason, the interaction.current_output will contain
    # u'2\nnter the number uniquely identifying this node in the replication cluster: '
    # which is probable cause of the next expect() to not work as expected. So
    # let's skip the expect()...
    # interaction.expect('Enter the number uniquely identifying this node in the replication cluster: ')
    interaction.send('3')
    interaction.expect('Enter the cluster database name: |vmdb_production| ')
    interaction.send('')
    interaction.expect('Enter the cluster database username: |root| ')
    interaction.send('')
    interaction.expect('Enter the cluster database password: ')
    interaction.send('qwe')
    interaction.expect('Enter the cluster database password: ')
    interaction.send('qwe')
    interaction.expect('Enter the primary database hostname or IP address: ')
    interaction.send(appl_db1.hostname)
    interaction.expect('Enter the Standby Server hostname or IP address: |.*| ')
    interaction.send('')
    interaction.expect('Configure Replication Manager \(repmgrd\) for automatic failover\? \(Y/N\): ')
    interaction.send('y')
    interaction.expect('Apply this Replication Server Configuration\? \(Y/N\): ')
    interaction.send('y')
    interaction.expect('Initialize postgresql disk complete', timeout=30)
    interaction.expect('Press any key to continue.', timeout=200)
    interaction.send('')


def start_failover_monitor(appl):
    interaction = SSHClientInteraction(appl.ssh_client, timeout=5, display=True)
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=100)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('8')
    interaction.expect('Choose the failover monitor configuration: ')
    interaction.send('1')
    interaction.expect('Press any key to continue.')
    interaction.send('')


def prepare_db_HA_deployment(appl_db1, appl_evm, appl_db2):
    for appl in (appl_db1, appl_evm, appl_db2):
        appl.wait_for_ssh()
    deploy_primary_db(appl_db1)
    deploy_evm(appl_evm, appl_db1)
    configure_db_replication(appl_db1)
    deploy_standby_db(appl_db2, appl_db1)
    start_failover_monitor(appl_db1)
    start_failover_monitor(appl_db2)
    start_failover_monitor(appl_evm)


def test_appliance_console_HA_setup_DC(three_temp_appliances_unconfig_funcscope_rhevm):
    appl_db1, appl_evm, appl_db2 = three_temp_appliances_unconfig_funcscope_rhevm
    prepare_db_HA_deployment(appl_db1, appl_evm, appl_db2)
    navigate_to(appl_evm.server, 'LoggedIn')

