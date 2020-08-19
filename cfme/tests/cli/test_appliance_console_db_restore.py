import re
from collections import namedtuple

import fauxfactory
import pytest
from wait_for import wait_for

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.cli import provider_app_crud
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.console import configure_appliances_ha
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import manager
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker

pytestmark = [
    test_requirements.restore
]

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])

evm_log = '/var/www/miq/vmdb/log/evm.log'


def provision_vm(request, provider):
    """Function to provision appliance to the provider being tested"""
    vm_name = fauxfactory.gen_alphanumeric(16, start="test_rest_db_")
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
    takes a backup on the first one prior to running tests.
    """
    appl1, appl2 = temp_appliances_unconfig_funcscope_rhevm
    # configure appliances
    appl1.configure(region=0)
    appl2.configure(region=0)

    for app in temp_appliances_unconfig_funcscope_rhevm:
        app.wait_for_miq_ready()

    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(OpenStackProvider, appl1).setup()
    appl1.db.backup()
    appl1.wait_for_miq_ready()
    return temp_appliances_unconfig_funcscope_rhevm


@pytest.fixture
def get_appliance_with_ansible(temp_appliance_preconfig_funcscope):
    """Returns database-owning appliance, enables embedded ansible,
    waits for the ansbile to get ready, takes a backup prior to running
    tests.
    """
    appl1 = temp_appliance_preconfig_funcscope
    # enable embedded ansible and create pg_basebackup
    appl1.enable_embedded_ansible_role()
    appl1.wait_for_embedded_ansible()
    appl1.db.backup()
    appl1.wait_for_miq_ready()
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
    appl1.wait_for_miq_ready()

    appl2.appliance_console_cli.configure_appliance_external_join(
        app_ip, app_creds_modscope['username'], app_creds_modscope['password'], 'vmdb_production',
        app_ip, app_creds_modscope['sshlogin'], app_creds_modscope['sshpass'])
    appl2.wait_for_miq_ready()
    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(OpenStackProvider, appl1).setup()
    appl1.db.backup()
    return temp_appliances_unconfig_funcscope_rhevm


def fetch_v2key(appl1, appl2):
    # Fetch v2_key and database.yml from the first appliance
    rand_v2_filename = f"/tmp/v2_key_{fauxfactory.gen_alphanumeric()}"
    rand_yml_filename = f"/tmp/database_yml_{fauxfactory.gen_alphanumeric()}"
    appl1.ssh_client.get_file("/var/www/miq/vmdb/certs/v2_key", rand_v2_filename)
    appl2.ssh_client.put_file(rand_v2_filename, "/var/www/miq/vmdb/certs/v2_key")
    appl1.ssh_client.get_file("/var/www/miq/vmdb/config/database.yml", rand_yml_filename)
    appl2.ssh_client.put_file(rand_yml_filename, "/var/www/miq/vmdb/config/database.yml")


def fetch_db_local(appl1, appl2, file_name):
    # Fetch db from the first appliance
    dump_filename = f"/tmp/db_dump_{fauxfactory.gen_alphanumeric()}"
    appl1.ssh_client.get_file(file_name, dump_filename)
    appl2.ssh_client.put_file(dump_filename, file_name)


@pytest.fixture
def two_appliances_one_with_providers(temp_appliances_preconfig_funcscope):
    """Requests two configured appliances from sprout."""
    appl1, appl2 = temp_appliances_preconfig_funcscope

    # Add infra/cloud providers
    provider_app_crud(VMwareProvider, appl1).setup()
    provider_app_crud(OpenStackProvider, appl1).setup()
    return appl1, appl2


def restore_db(appl, location=''):
    with SSHExpect(appl) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '6',
            '5.11.2.1': 4
        }))
        interaction.answer(re.escape('Choose the restore database file source: |1| '), '1')
        interaction.answer(re.escape('Enter the location of the local restore file: '
                                '|/tmp/evm_db.backup| '), location)
        interaction.answer(re.escape('Should this file be deleted after completing the restore? '
                                '(Y/N): '), 'N')
        interaction.answer(re.escape(
            'Are you sure you would like to restore the database? (Y/N): '), 'Y')
        interaction.answer('Press any key to continue.', '', timeout=60)


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_dump_restore_db_local(request, get_appliances_with_providers):
    """ Test single appliance dump and restore, configures appliance with providers,
    dumps a database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
    """
    appl1, appl2 = get_appliances_with_providers
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)
    fetch_db_local(appl1, appl2, "/tmp/evm_db.backup")
    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()
    restore_db(appl2)
    appl2.evmserverd.start()
    appl2.wait_for_miq_ready()

    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == set(appl1.managed_provider_names), (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_backup_restore_db_local(request, two_appliances_one_with_providers):
    """ Test single appliance backup and restore, configures appliance with providers,
    backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
    """
    appl1, appl2 = two_appliances_one_with_providers
    appl1_provider_names = set(appl1.managed_provider_names)

    backup_file_name = f'/tmp/backup.{fauxfactory.gen_alphanumeric()}.dump'
    appl1.db.backup(backup_file_name)

    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)
    fetch_db_local(appl1, appl2, backup_file_name)

    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()

    with SSHExpect(appl2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '6',
            '5.11.2.1': 4
        }))
        interaction.answer(
            re.escape('Choose the restore database file source: |1| '), '')
        interaction.answer(
            re.escape('Enter the location of the local restore file: |/tmp/evm_db.backup| '),
            backup_file_name)
        interaction.answer(
            re.escape('Should this file be deleted after completing the restore? (Y/N): '), 'n')
        interaction.answer(
            re.escape('Are you sure you would like to restore the database? (Y/N): '), 'y')
        interaction.answer('Press any key to continue.', '', timeout=80)

    appl2.evmserverd.start()
    appl2.wait_for_miq_ready()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == appl1_provider_names, (
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
    restore_db(appl1, '/tmp/evm_db.backup')
    manager.quit()
    appl1.evmserverd.start()
    appl1.wait_for_miq_ready()
    appl1.wait_for_embedded_ansible()
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
        request, replicated_appliances_with_providers):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1/2h
        upstream: no
    """
    appl1, appl2 = replicated_appliances_with_providers
    appl1.db.backup()
    appl2.db.backup()

    providers_before_restore = set(appl1.managed_provider_names)
    # Restore DB on the second appliance
    appl2.set_pglogical_replication(replication_type=':none')
    appl1.set_pglogical_replication(replication_type=':none')
    appl1.evmserverd.stop()
    appl2.evmserverd.stop()
    appl1.db_service.restart()
    appl2.db_service.restart()
    restore_db(appl1, '/tmp/evm_db.backup')
    restore_db(appl2, '/tmp/evm_db.backup')
    appl1.evmserverd.start()
    appl2.evmserverd.start()
    appl1.wait_for_miq_ready()
    appl2.wait_for_miq_ready()

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
    appl1.wait_for_miq_ready()
    appl2.evmserverd.start()
    appl2.wait_for_miq_ready()
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
        request, replicated_appliances_with_providers):
    """
    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Configuration
        initialEstimate: 1h
    """
    appl1, appl2 = replicated_appliances_with_providers
    appl1.db.backup()
    appl2.db.backup()
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
    appl1.wait_for_miq_ready()
    appl2.wait_for_miq_ready()

    # reconfigure replication between appliances which switches to "disabled"
    # during restore
    appl2.set_pglogical_replication(replication_type=':none')
    expected_providers = [] if appl2.version < '5.11' else ['Embedded Ansible']
    assert appl2.managed_provider_names == expected_providers

    # Start the replication again
    appl2.set_pglogical_replication(replication_type=':global')
    appl2.add_pglogical_replication_subscription(appl1.hostname)

    # Assert providers exist after restore and replicated to second appliances
    assert providers_before_restore == set(appl1.managed_provider_names)
    wait_for(
        lambda: providers_before_restore == set(appl2.managed_provider_names),
        timeout=20
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
@pytest.mark.meta(automates=[1740515, 1693189])
def test_appliance_console_restore_db_ha(request, unconfigured_appliances, app_creds):
    """Configure HA environment with providers, run backup/restore on configuration,
    Confirm that ha failover continues to work correctly and providers still exist.

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    Bugzilla:
        1693189
        1740515
    """
    pwd = app_creds["password"]
    appl1, appl2, appl3 = configure_appliances_ha(unconfigured_appliances, pwd)

    # Add infra/cloud providers and create db backup
    provider_app_crud(VMwareProvider, appl3).setup()
    provider_app_crud(OpenStackProvider, appl3).setup()
    appl1.db.backup()

    providers_before_restore = set(appl3.managed_provider_names)
    # Restore DB on the second appliance
    appl3.evmserverd.stop()
    appl1.repmgr.stop()
    appl2.repmgr.stop()
    appl1.db.drop()
    appl1.db.create()
    fetch_v2key(appl3, appl1)
    restore_db(appl1)

    appl1.appliance_console.reconfigure_primary_replication_node(pwd)
    appl2.appliance_console.reconfigure_standby_replication_node(pwd, appl1.hostname)

    appl3.appliance_console.configure_automatic_failover(primary_ip=appl1.hostname)
    appl3.evm_failover_monitor.restart()

    appl3.evmserverd.start()
    appl3.wait_for_miq_ready()
    # Assert providers still exist after restore
    assert providers_before_restore == set(appl3.managed_provider_names), (
        'Restored DB is missing some providers'
    )

    with LogValidator(evm_log,
                      matched_patterns=['Starting to execute failover'],
                      hostname=appl3.hostname).waiting(timeout=450):
        # Cause failover to occur
        appl1.db_service.stop()

    appl3.evmserverd.wait_for_running()
    appl3.wait_for_miq_ready()
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
@pytest.mark.meta(automates=[1633573])
def test_appliance_console_restore_db_nfs(request, two_appliances_one_with_providers,
                                          utility_vm, utility_vm_nfs_ip):
    """ Test single appliance backup and restore through nfs, configures appliance with providers,
        backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1h

    Bugzilla:
        1633573
    """
    appl1, appl2 = two_appliances_one_with_providers
    vm, _, data = utility_vm
    host = utility_vm_nfs_ip
    loc = data['network_share']['nfs']['path']
    nfs_dump_file_name = f'/tmp/backup.{fauxfactory.gen_alphanumeric()}.dump'
    nfs_restore_dir_path = f'nfs://{host}{loc}'
    nfs_restore_file_path = f'{nfs_restore_dir_path}/db_backup/{nfs_dump_file_name}'
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)

    appl1_provider_names = set(appl1.managed_provider_names)

    # Do the backup
    with SSHExpect(appl1) as interaction:
        appl1.evmserverd.stop()
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '4',
            '5.11.2.1': 2
        }))
        interaction.answer(r'Choose the backup output file destination: \|1\| ', '2')
        interaction.answer(r'Enter the location to save the backup file to: \|.*\| ',
            nfs_dump_file_name)
        # Enter the location to save the remote backup file to
        interaction.answer(
            re.escape('Example: nfs://host.mydomain.com/exported/my_exported_folder/db.backup: '),
            nfs_restore_dir_path)
        # Running Database backup to nfs://XX.XX.XX.XX/srv/export...
        interaction.answer('Press any key to continue.', '', timeout=240)

    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()

    with SSHExpect(appl2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '6',
            '5.11.2.1': 4
        }))
        interaction.answer(r'Choose the restore database file source: \|1\| ', '2')
        # Enter the location of the remote backup file
        interaction.answer(
            re.escape('Example: nfs://host.mydomain.com/exported/my_exported_folder/db.backup: '),
            nfs_restore_file_path)
        interaction.answer(r'Are you sure you would like to restore the database\? \(Y\/N\): ', 'y')
        interaction.answer('Press any key to continue.', '', timeout=80)

    appl2.evmserverd.start()
    appl2.wait_for_miq_ready()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == appl1_provider_names, (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_appliance_console_restore_db_samba(request, two_appliances_one_with_providers,
                                            utility_vm, utility_vm_samba_ip):
    """ Test single appliance backup and restore through smb, configures appliance with providers,
        backs up database, restores it to fresh appliance and checks for matching providers.

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        caseimportance: critical
        initialEstimate: 1h
    """
    appl1, appl2 = two_appliances_one_with_providers
    _, _, data = utility_vm
    host = utility_vm_samba_ip
    loc = data['network_share']['smb']['path']
    smb_dump_file_name = f'/tmp/backup.{fauxfactory.gen_alphanumeric()}.dump'
    smb_restore_dir_path = f'smb://{host}{loc}'
    smb_restore_file_path = f'{smb_restore_dir_path}/db_backup/{smb_dump_file_name}'

    creds_key = data['network_share']['smb']['credentials']
    pwd = credentials[creds_key]['password']
    usr = credentials[creds_key]['username']
    # Transfer v2_key and db backup from first appliance to second appliance
    fetch_v2key(appl1, appl2)

    appl1_provider_names = set(appl1.managed_provider_names)

    # Do the backup
    with SSHExpect(appl1) as interaction:
        appl1.evmserverd.stop()
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '4',
            '5.11.2.1': 2
        }))
        interaction.answer(r'Choose the backup output file destination: \|1\| ', '3')
        interaction.answer(r'Enter the location to save the backup file to: \|.*\| ',
            smb_dump_file_name)
        # Enter the location to save the remote backup file to
        interaction.answer(
            re.escape('Example: smb://host.mydomain.com/my_share/daily_backup/db.backup: '),
            smb_restore_dir_path)
        # Enter the username with access to this file.
        interaction.answer(re.escape("Example: 'mydomain.com/user': "), usr)
        interaction.answer(re.escape(f'Enter the password for {usr}: '), pwd)
        # Running Database backup to nfs://10.8.198.142/srv/export...
        interaction.answer('Press any key to continue.', '', timeout=120)

    # Restore DB on the second appliance
    appl2.evmserverd.stop()
    appl2.db.drop()
    appl2.db.create()

    with SSHExpect(appl2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=40)
        interaction.answer('Choose the advanced setting: ', VersionPicker({
            LOWEST: '6',
            '5.11.2.1': 4
        }))
        interaction.answer(r'Choose the restore database file source: \|1\| ', '3')
        # Enter the location of the remote backup file
        interaction.answer(
            re.escape('Example: smb://host.mydomain.com/my_share/daily_backup/db.backup: '),
            smb_restore_file_path)
        # Enter the username with access to this file.
        interaction.answer(re.escape("Example: 'mydomain.com/user': "), usr)
        interaction.answer(re.escape(f'Enter the password for {usr}: '), pwd)
        interaction.answer(r'Are you sure you would like to restore the database\? \(Y\/N\): ', 'y')
        interaction.answer('Press any key to continue.', '', timeout=80)

    appl2.evmserverd.start()
    appl2.wait_for_miq_ready()
    # Assert providers on the second appliance
    assert set(appl2.managed_provider_names) == appl1_provider_names, (
        'Restored DB is missing some providers'
    )
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appl2)
    vm = provision_vm(request, virtual_crud)
    assert vm.mgmt.is_running, "vm not running"
