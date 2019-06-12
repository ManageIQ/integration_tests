from collections import namedtuple

import fauxfactory
import pytest
from paramiko_expect import SSHClientInteraction
from wait_for import wait_for

from cfme.cloud.provider.ec2 import EC2Provider
from cfme.fixtures.cli import provider_app_crud
from cfme.fixtures.cli import replicated_appliances_with_providers
from cfme.fixtures.cli import waiting_for_ha_monitor_started
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import manager
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.ssh import SSHClient

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])

evm_log = '/var/www/miq/vmdb/log/evm.log'


def provision_vm(request, provider):
    """Function to provision appliance to the provider being tested"""
    vm_name = "test_rest_db_{}".format(fauxfactory.gen_alphanumeric())
    coll = provider.appliance.provider_based_collection(provider, coll_type='vms')
    vm = coll.instantiate(vm_name, provider)
    request.addfinalizer(vm.cleanup_on_provider)
    if not provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %s on provider %s", vm_name, provider.key)
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm %s on provider %s", vm_name, provider.key)
    vm.provider.refresh_provider_relationships()
    return vm


@pytest.fixture
def get_appliances_with_providers(temp_appliances_unconfig_funcscope_rhevm):
    """Returns two database-owning appliances, configures first appliance with providers and
    takes a backup prior to running tests.

    """
    appl1, appl2 = temp_appliances_unconfig_funcscope_rhevm
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_web_ui()
    appl2.configure(region=0)
    appl2.wait_for_web_ui()
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(EC2Provider, appl1).setup()
    appl1.db.backup()
    return temp_appliances_unconfig_funcscope_rhevm


@pytest.fixture
def get_replicated_appliances_with_providers(temp_appliances_unconfig_funcscope_rhevm):
    """Returns two database-owning appliances, configures first appliance with provider,
    enables embedded ansible, takes a pg_backup and copys it to second appliance
    prior to running tests.

    """
    appl1, appl2 = replicated_appliances_with_providers(temp_appliances_unconfig_funcscope_rhevm)
    appl1.ssh_client.run_command("pg_basebackup -x -Ft -z -D /tmp/backup")
    appl1.db.backup()
    appl2.ssh_client.run_command("pg_basebackup -x -Ft -z -D /tmp/backup")
    appl2.db.backup()
    return temp_appliances_unconfig_funcscope_rhevm


@pytest.fixture
def get_appliance_with_ansible(temp_appliance_preconfig_funcscope):
    """Returns database-owning appliance, enables embedded ansible,
    takes a pg_backup prior to running tests.

    """
    appl1 = temp_appliance_preconfig_funcscope
    # enable embedded ansible and create pg_basebackup
    appl1.enable_embedded_ansible_role()
    assert appl1.is_embedded_ansible_running
    appl1.ssh_client.run_command("pg_basebackup -x -Ft -z -D /tmp/backup")
    return temp_appliance_preconfig_funcscope


@pytest.fixture
def get_ext_appliances_with_providers(temp_appliances_unconfig_funcscope_rhevm, app_creds_modscope):
    """Returns two database-owning appliances, configures first appliance with providers and
    takes a backup prior to running tests.

    """
    appl1, appl2 = temp_appliances_unconfig_funcscope_rhevm
    app_ip = appl1.hostname
    # configure appliances
    appl1.configure(region=0)
    appl1.wait_for_web_ui()
    appl2.appliance_console_cli.configure_appliance_external_join(
        app_ip, app_creds_modscope['username'], app_creds_modscope['password'], 'vmdb_production',
        app_ip, app_creds_modscope['sshlogin'], app_creds_modscope['sshpass'])
    appl2.wait_for_web_ui()
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(EC2Provider, appl1).setup()
    appl1.db.backup()
    return temp_appliances_unconfig_funcscope_rhevm


@pytest.fixture
def get_ha_appliances_with_providers(unconfigured_appliances, app_creds):
    """Configure HA environment

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '7' setup db, '1' Creates v2_key, '1' selects internal db,
    '2' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    360 secs and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '7' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait 360 seconds and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '8' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '8' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait 360 seconds to configure, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '10' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    """
    appl1, appl2, appl3 = unconfigured_appliances
    app0_ip = appl1.hostname
    app1_ip = appl2.hostname
    pwd = app_creds['password']
    # Configure first appliance as dedicated database
    command_set = ('ap', '', '7', '1', '2', 'y', pwd, TimedCommand(pwd, 360), '')
    appl1.appliance_console.run_commands(command_set)
    wait_for(lambda: appl1.db.is_dedicated_active)
    # Configure EVM webui appliance with create region in dedicated database
    command_set = ('ap', '', '7', '2', app0_ip, '', pwd, '', '2', '0', 'y', app0_ip, '', '', '',
        pwd, TimedCommand(pwd, 360), '')
    appl3.appliance_console.run_commands(command_set)
    appl3.evmserverd.wait_for_running()
    appl3.wait_for_web_ui()
    # Configure primary replication node
    command_set = ('ap', '', '8', '1', '1', '', '', pwd, pwd, app0_ip, 'y',
        TimedCommand('y', 60), '')
    appl1.appliance_console.run_commands(command_set)
    # Configure secondary replication node
    command_set = ('ap', '', '8', '2', '2', app0_ip, '', pwd, '', '1', '2', '', '', pwd, pwd,
                   app0_ip, app1_ip, 'y', TimedCommand('y', 60), '')
    appl2.appliance_console.run_commands(command_set)
    # Configure automatic failover on EVM appliance
    command_set = ('ap', '', '10', TimedCommand('1', 30), '')
    appl3.appliance_console.run_commands(command_set)

    with waiting_for_ha_monitor_started(appl3, app1_ip, timeout=300):
        # Configure automatic failover on EVM appliance
        command_set = ('ap', '', '8', TimedCommand('1', 30), '')
        appl3.appliance_console.run_commands(command_set)

    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl3).setup()
    provider_app_crud(EC2Provider, appl3).setup()
    appl1.db.backup()

    return unconfigured_appliances


def fetch_v2key(appl1, appl2):
    # Fetch v2_key and database.yml from the first appliance
    rand_v2_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
    rand_yml_filename = "/tmp/database_yml_{}".format(fauxfactory.gen_alphanumeric())
    appl1.ssh_client.get_file("/var/www/miq/vmdb/certs/v2_key", rand_v2_filename)
    appl2.ssh_client.put_file(rand_v2_filename, "/var/www/miq/vmdb/certs/v2_key")
    appl1.ssh_client.get_file("/var/www/miq/vmdb/config/database.yml", rand_yml_filename)
    appl2.ssh_client.put_file(rand_yml_filename, "/var/www/miq/vmdb/config/database.yml")


def fetch_db_local(appl1, appl2):
    # Fetch db from the first appliance
    dump_filename = "/tmp/db_dump_{}".format(fauxfactory.gen_alphanumeric())
    appl1.ssh_client.get_file("/tmp/evm_db.backup", dump_filename)
    appl2.ssh_client.put_file(dump_filename, "/tmp/evm_db.backup")


def setup_nfs_samba_backup(appl1):
    # Fetch db from first appliance and push it to nfs/samba server
    connect_kwargs = {
        'hostname': cfme_data['network_share']['hostname'],
        'username': credentials['ssh']['username'],
        'password': credentials['depot_credentials']['password']
    }
    loc = cfme_data['network_share']['nfs_path']
    nfs_smb = SSHClient(**connect_kwargs)
    dump_filename = "/tmp/db_dump_{}".format(fauxfactory.gen_alphanumeric())
    appl1.ssh_client.get_file("/tmp/evm_db.backup", dump_filename)
    nfs_smb.put_file(dump_filename, "{}share.backup".format(loc))


def logging_callback(appliance):
    # TODO (jhenner) Remove me. This is being defined also in some other PR:
    # Fix minor version update tests. #8521
    def the_logger(m):
        logger.debug('Appliance %s:\n%s', appliance.hostname, m)
    return the_logger


def restore_db(appl, location=''):
    interaction = SSHClientInteraction(appl.ssh_client, timeout=10, display=True,
                                       output_callback=logging_callback(appl))
    interaction.send('ap')
    interaction.expect('Press any key to continue.', timeout=20)
    interaction.send('')
    interaction.expect('Choose the advanced setting: ')
    interaction.send('6')
    interaction.expect('Choose the restore database file source: |1| ')
    interaction.send('1')
    interaction.expect('Enter the location of the local restore file: |/tmp/evm_db.backup| ')
    interaction.send(location)
    interaction.expect(r'Should this file be deleted after completing the restore\? \(Y\/N\): ')
    interaction.send('N')
    interaction.expect(r'Are you sure you would like to restore the database\? \(Y\/N\): ')
    interaction.send('Y')
    interaction.expect('Press any key to continue.', timeout=60)


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_local(request, get_appliances_with_providers):
    """ Test single appliance backup and restore, configures appliance with providers,
    backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
    """
    appl1, appl2 = get_appliances_with_providers
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)
    fetch_db_local(appl1, appl2)
    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()
    restore_db(appl2)
    appl2.evmserverd.start()
    appl2.wait_for_web_ui()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_pg_basebackup_ansible(get_appliance_with_ansible):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
    """
    appl1 = get_appliance_with_ansible
    # Restore DB on the second appliance
    appl1.evmserverd.stop()
    appl1.db_service.restart()
    restore_db(appl1, '/tmp/backup/base.tar.gz')
    manager.quit()
    appl1.evmserverd.start()
    appl1.wait_for_web_ui()
    appl1.reboot()
    appl1.evmserverd.start()
    appl1.wait_for_web_ui()
    appl1.ssh_client.run_command(
        'curl -kL https://localhost/ansibleapi | grep "Ansible Tower REST API"')
    repositories = appl1.collections.ansible_repositories
    try:
        repository = repositories.create(
            name='example',
            url=cfme_data.ansible_links.playbook_repositories.console_db,
            description='example')
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
    view = navigate_to(repository, "Details")
    refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh,
        message="Check if playbook repo added"
    )


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_pg_basebackup_replicated(
        request, get_replicated_appliances_with_providers):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
        upstream: no
    """
    appl1, appl2 = get_replicated_appliances_with_providers
    providers_before_restore = set(appl1.managed_provider_names)
    # Restore DB on the second appliance
    appl2.set_pglogical_replication(replication_type=':none')
    appl1.set_pglogical_replication(replication_type=':none')
    appl1.evmserverd.stop()
    appl2.evmserverd.stop()
    appl1.db_service.restart()
    appl2.db_service.restart()
    restore_db(appl1, '/tmp/backup/base.tar.gz')
    restore_db(appl2, '/tmp/backup/base.tar.gz')
    appl1.evmserverd.start()
    appl2.evmserverd.start()
    appl1.wait_for_web_ui()
    appl2.wait_for_web_ui()
    # Assert providers exist after restore and replicated to second appliances
    assert providers_before_restore == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    assert providers_before_restore == set(appl2.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, appl1)
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, appl2)
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    assert vm1.mgmt.is_running, "vm not running"
    assert vm2.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_external(request, get_ext_appliances_with_providers):
    """Configure ext environment with providers, run backup/restore on configuration,
    Confirm that providers still exist after restore and provisioning works.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1h
    """
    appl1, appl2 = get_ext_appliances_with_providers
    # Restore DB on the second appliance
    providers_before_restore = set(appl1.managed_provider_names)
    appl2.evmserverd.stop()
    appl1.evmserverd.stop()
    appl1.db_service.restart()
    appl1.db.drop()
    appl1.db.create()
    restore_db(appl1)
    appl1.evmserverd.start()
    appl1.wait_for_web_ui()
    appl2.evmserverd.start()
    appl2.wait_for_web_ui()
    # Assert providers after restore on both apps
    assert providers_before_restore == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    assert providers_before_restore == set(appl2.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, appl1)
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, appl2)
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    assert vm1.mgmt.is_running, "vm not running"
    assert vm2.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_replicated(
        request, get_replicated_appliances_with_providers):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Configuration
        initialEstimate: 1h
    """
    appl1, appl2 = get_replicated_appliances_with_providers
    providers_before_restore = set(appl1.managed_provider_names)
    # Restore DB on the second appliance
    appl2.evmserverd.stop()

    restore_db(appl2)
    # Restore db on first appliance
    appl1.set_pglogical_replication(replication_type=':none')
    appl1.evmserverd.stop()
    appl1.db.drop()
    appl1.db.create()
    restore_db(appl1)
    appl1.evmserverd.start()
    appl2.evmserverd.start()
    appl1.wait_for_web_ui()
    appl2.wait_for_web_ui()
    # reconfigure replication between appliances, lost during restore
    appl1.set_pglogical_replication(replication_type=':remote')
    appl2.set_pglogical_replication(replication_type=':global')
    appl2.add_pglogical_replication_subscription(appl1.hostname)
    # Assert providers exist after restore and replicated to second appliances
    assert providers_before_restore == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    assert providers_before_restore == set(appl2.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, appl1)
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, appl2)
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    assert vm1.mgmt.is_running, "vm not running"
    assert vm2.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_ha(request, get_ha_appliances_with_providers):
    """Configure HA environment with providers, run backup/restore on configuration,
    Confirm that ha failover continues to work correctly and providers still exist.

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    appl1, appl2, appl3 = get_ha_appliances_with_providers
    providers_before_restore = set(appl3.managed_provider_names)
    # Restore DB on the second appliance
    appl3.evmserverd.stop()
    appl1.ssh_client.run_command("systemctl stop rh-postgresql95-repmgr")
    appl2.ssh_client.run_command("systemctl stop rh-postgresql95-repmgr")
    appl1.db.drop()
    appl1.db.create()
    fetch_v2key(appl3, appl1)
    restore_db(appl1)
    appl1.ssh_client.run_command("systemctl start rh-postgresql95-repmgr")
    appl2.ssh_client.run_command("systemctl start rh-postgresql95-repmgr")
    appl3.evmserverd.start()
    appl3.wait_for_web_ui()
    # Assert providers still exist after restore
    assert providers_before_restore == set(appl3.managed_provider_names), (
        'Restored DB is missing some providers'
    )

    with LogValidator(evm_log,
                      matched_patterns=['Starting to execute failover'],
                      hostname=appl3.hostname).waiting(timeout=450):
        # Cause failover to occur
        result = appl1.ssh_client.run_command(
            'systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
        assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    appl3.evmserverd.wait_for_running()
    appl3.wait_for_web_ui()
    # Assert providers still exist after ha failover
    assert providers_before_restore == set(appl3.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs after restore/failover
    virtual_crud = provider_app_crud(VMwareProvider, appl3)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_nfs(request, get_appliances_with_providers):
    """ Test single appliance backup and restore through nfs, configures appliance with providers,
        backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1h
    """
    appl1, appl2 = get_appliances_with_providers
    host = cfme_data['network_share']['hostname']
    loc = cfme_data['network_share']['nfs_path']
    nfs_dump = 'nfs://{}{}share.backup'.format(host, loc)
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)
    setup_nfs_samba_backup(appl1)
    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()
    command_set = ('ap', '', '4', '2', nfs_dump, TimedCommand('y', 60), '')
    appl2.appliance_console.run_commands(command_set)
    appl2.evmserverd.start()
    appl2.wait_for_web_ui()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_samba(request, get_appliances_with_providers):
    """ Test single appliance backup and restore through smb, configures appliance with providers,
        backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1h
    """
    appl1, appl2 = get_appliances_with_providers
    host = cfme_data['network_share']['hostname']
    loc = cfme_data['network_share']['smb_path']
    smb_dump = 'smb://{}{}share.backup'.format(host, loc)
    pwd = credentials['depot_credentials']['password']
    usr = credentials['depot_credentials']['username']
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)
    setup_nfs_samba_backup(appl1)
    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()
    command_set = ('ap', '', '4', '3', smb_dump, usr, pwd, TimedCommand('y', 60), '')
    appl2.appliance_console.run_commands(command_set)
    appl2.evmserverd.start()
    appl2.wait_for_web_ui()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"
