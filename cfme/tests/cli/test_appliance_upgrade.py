import fauxfactory
import pytest

from collections import namedtuple

from cfme.fixtures.cli import (provider_app_crud, provision_vm, upgrade_appliances,
                               do_appliance_versions_match)
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance import find_appliance, DummyAppliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.version import Version

from cfme.utils.wait import wait_for

REPOSITORIES = ["https://github.com/lcouzens/ansible_playbooks"]
TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
blocker_58z = BZ(1618795, forced_streams=['5.10'])

pytestmark = [
    pytest.mark.uncollectif(lambda appliance, old_version: (Version(old_version) < Version(5.9)) and
                            blocker_58z.blocks or appliance.is_pod,
                            reason="pod appliance should be updated thru openshift mechanism")

]


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is used for generating each major version and appending it to the empty
    versions list"""
    if isinstance(find_appliance(metafunc), DummyAppliance):
        pytest.skip()
    if metafunc.function:
        lowest = 7
    versions = []
    version = find_appliance(metafunc).version
    split_ver = str(version).split(".")
    for i in range(int(split_ver[1]) - 1, -1, -1):
        if i > lowest:
            versions.append("{}.{}".format(split_ver[0], i))
    metafunc.parametrize('old_version', versions, ids=[v for v in versions], indirect=True)


@pytest.fixture
def old_version(request):
    return request.param


def test_upgrade_single_inplace(appliance_preupdate, appliance, old_version):
    """Tests appliance upgrade between streams"""
    appliance_preupdate.evmserverd.stop()
    upgrade_appliances([appliance_preupdate])
    appliance_preupdate.db.migrate()
    appliance_preupdate.db.automate_reset()
    appliance_preupdate.db.restart_db_service()
    appliance_preupdate.start_evm_service()
    appliance_preupdate.wait_for_web_ui()
    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_preupdate),
             num_sec=300, delay=20, handle_exception=True,
             message='Waiting for appliance to upgrade')


@pytest.mark.ignore_stream("upstream")
def test_upgrade_enable_embedded_ansible(appliance_preupdate, appliance, old_version):
    """ Tests upgrading an appliance and then enabling embedded ansible, also confirms that repos
        can be added"""
    appliance_preupdate.evmserverd.stop()
    upgrade_appliances([appliance_preupdate])
    appliance_preupdate.db.migrate()
    appliance_preupdate.db.automate_reset()
    appliance_preupdate.db.restart_db_service()
    appliance_preupdate.start_evm_service()
    appliance_preupdate.wait_for_web_ui()
    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_preupdate),
             num_sec=300, delay=20, handle_exception=True,
             message='Waiting for appliance to upgrade')
    appliance_preupdate.enable_embedded_ansible_role()
    assert appliance_preupdate.is_embedded_ansible_running
    assert wait_for(func=lambda: appliance_preupdate.is_embedded_ansible_running, num_sec=300,
                    message='Waiting for ansible role to start')
    assert wait_for(func=lambda: appliance_preupdate.is_rabbitmq_running, num_sec=30,
                    message='Waiting for rabbitmq service to start')
    assert wait_for(func=lambda: appliance_preupdate.is_nginx_running, num_sec=30,
                    message='Waiting for nginx service to start')
    repositories = appliance_preupdate.collections.ansible_repositories
    name = "example_{}".format(fauxfactory.gen_alpha())
    description = "edited_{}".format(fauxfactory.gen_alpha())
    repository = repositories.create(
        name,
        REPOSITORIES[0],
        description=description)
    view = navigate_to(repository, "Details")
    refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status").lower() == "successful",
        timeout=60,
        fail_func=refresh
    )


@pytest.mark.ignore_stream("upstream")
def test_upgrade_inplace_scap_single(appliance_preupdate, appliance, old_version):
    """ Tests updating an appliance with providers and scap hardened, also confirms that the
        provisioning continues to function correctly after the update has completed"""
    appliance_preupdate.appliance_console.scap_harden_appliance()
    rules_failures = appliance_preupdate.appliance_console.scap_check_rules()
    assert not rules_failures, "Some rules have failed, check log"
    appliance_preupdate.evmserverd.stop()
    upgrade_appliances([appliance_preupdate])
    appliance_preupdate.db.migrate()
    appliance_preupdate.db.automate_reset()
    appliance_preupdate.db.restart_db_service()
    appliance_preupdate.start_evm_service()
    appliance_preupdate.wait_for_web_ui()
    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_preupdate),
             num_sec=300, delay=20, handle_exception=True,
             message='Waiting for appliance to upgrade')
    # Confirm rules are still applied.
    rules_failures = appliance_preupdate.appliance_console.scap_check_rules()
    assert not rules_failures, "Some rules have failed, check log"


@pytest.mark.ignore_stream("upstream")
def test_upgrade_inplace_distributed(ext_appliances_with_providers, appliance, request,
                                     old_version, soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed"""
    ext_appliances_with_providers[0].evmserverd.stop()
    ext_appliances_with_providers[1].evmserverd.stop()
    upgrade_appliances(ext_appliances_with_providers)
    ext_appliances_with_providers[0].db.migrate()
    ext_appliances_with_providers[0].db.automate_reset()
    ext_appliances_with_providers[0].db.restart_db_service()
    ext_appliances_with_providers[0].start_evm_service()
    ext_appliances_with_providers[1].start_evm_service()
    ext_appliances_with_providers[0].wait_for_web_ui()
    ext_appliances_with_providers[1].wait_for_web_ui()
    wait_for(do_appliance_versions_match, func_args=(appliance, ext_appliances_with_providers[0]),
             num_sec=300, delay=20, handle_exception=True,
             message='Waiting for appliance to upgrade')
    wait_for(do_appliance_versions_match, func_args=(appliance, ext_appliances_with_providers[1]),
             num_sec=300, delay=20, handle_exception=True,
             message='Waiting for appliance to upgrade')
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[0])
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[1])
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    soft_assert(vm1.provider.mgmt.does_vm_exist(vm1.name), "vm not provisioned")
    soft_assert(vm2.provider.mgmt.does_vm_exist(vm2.name), "vm not provisioned")


@pytest.mark.ignore_stream("upstream")
def test_upgrade_inplace_replicated(replicated_appliances_with_providers, appliance, request,
                                    old_version, soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed"""
    providers_before_upgrade = set(replicated_appliances_with_providers[0].managed_provider_names)
    replicated_appliances_with_providers[0].evmserverd.stop()
    replicated_appliances_with_providers[1].evmserverd.stop()
    upgrade_appliances(replicated_appliances_with_providers)
    replicated_appliances_with_providers[0].ssh_client.run_command(
        'systemctl restart $APPLIANCE_PG_SERVICE')
    replicated_appliances_with_providers[1].ssh_client.run_command(
        'systemctl restart $APPLIANCE_PG_SERVICE')
    replicated_appliances_with_providers[0].db.migrate()
    replicated_appliances_with_providers[1].db.migrate()
    replicated_appliances_with_providers[0].db.automate_reset()
    replicated_appliances_with_providers[1].db.automate_reset()
    replicated_appliances_with_providers[0].db.restart_db_service()
    replicated_appliances_with_providers[1].db.restart_db_service()
    replicated_appliances_with_providers[0].start_evm_service()
    replicated_appliances_with_providers[1].start_evm_service()
    replicated_appliances_with_providers[0].wait_for_web_ui()
    replicated_appliances_with_providers[1].wait_for_web_ui()
    wait_for(
        do_appliance_versions_match, func_args=(appliance, replicated_appliances_with_providers[0]),
        num_sec=300, delay=20, handle_exception=True, message='Waiting for appliance to upgrade'
    )
    wait_for(
        do_appliance_versions_match, func_args=(appliance, replicated_appliances_with_providers[1]),
        num_sec=300, delay=20, handle_exception=True, message='Waiting for appliance to upgrade'
    )
    # Assert providers exist after upgrade and replicated to second appliances
    assert providers_before_upgrade == set(
        replicated_appliances_with_providers[1].managed_provider_names), 'Providers are missing'
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, replicated_appliances_with_providers[0])
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, replicated_appliances_with_providers[1])
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    soft_assert(vm1.provider.mgmt.does_vm_exist(vm1.name), "vm not provisioned")
    soft_assert(vm2.provider.mgmt.does_vm_exist(vm2.name), "vm not provisioned")


@pytest.mark.ignore_stream("upstream")
def test_upgrade_inplace_ha(ha_appliances_with_providers, appliance, request,
                            old_version):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed"""
    ha_appliances_with_providers[2].evmserverd.stop()
    upgrade_appliances(ha_appliances_with_providers)
    ha_appliances_with_providers[0].ssh_client.run_command(
        'systemctl restart $APPLIANCE_PG_SERVICE')
    ha_appliances_with_providers[1].ssh_client.run_command(
        'systemctl restart $APPLIANCE_PG_SERVICE')
    # Run migration on non-VMDB appliance for dedicated external configurations
    result = ha_appliances_with_providers[2].ssh_client.run_rake_command("db:migrate", timeout=300)
    assert result.success, "Failed to migrate new database: {}".format(result.output)
    result = ha_appliances_with_providers[2].ssh_client.run_rake_command(
        r'db:migrate:status 2>/dev/null | grep "^\s*down"', timeout=30)
    assert result.failed, ("Migration failed; migrations in 'down' state found: {}"
                           .format(result.output))
    ha_appliances_with_providers[2].db.automate_reset()
    ha_appliances_with_providers[1].db.restart_db_service()
    ha_appliances_with_providers[2].start_evm_service()
    ha_appliances_with_providers[2].wait_for_web_ui()
    wait_for(
        do_appliance_versions_match, func_args=(appliance, ha_appliances_with_providers[0]),
        num_sec=900, delay=20, handle_exception=True, message='Waiting for appliance to upgrade'
    )
    wait_for(
        do_appliance_versions_match, func_args=(appliance, ha_appliances_with_providers[1]),
        num_sec=300, delay=20, handle_exception=True, message='Waiting for appliance to upgrade'
    )
    wait_for(
        do_appliance_versions_match, func_args=(appliance, ha_appliances_with_providers[2]),
        num_sec=300, delay=20, handle_exception=True, message='Waiting for appliance to upgrade'
    )
    # Cause failover to occur
    result = ha_appliances_with_providers[0].ssh_client.run_command(
        'systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    def is_failover_started():
        return ha_appliances_with_providers[2].ssh_client.run_command(
            "grep 'Starting to execute failover' /var/www/miq/vmdb/log/ha_admin.log").success

    wait_for(is_failover_started, timeout=300, delay=20, handle_exception=True,
             message='Waiting for HA failover')
    ha_appliances_with_providers[2].wait_for_evm_service()
    ha_appliances_with_providers[2].wait_for_web_ui()
    # Verify that existing provider can detect new VMs
    virtual_crud = provider_app_crud(VMwareProvider, ha_appliances_with_providers[2])
    vm = provision_vm(request, virtual_crud)
    assert vm.provider.mgmt.does_vm_exist(vm.name), "vm not provisioned"
