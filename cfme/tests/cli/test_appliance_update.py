from collections import namedtuple

import fauxfactory
import pytest

from cfme.fixtures.cli import do_appliance_versions_match
from cfme.fixtures.cli import provider_app_crud
from cfme.fixtures.cli import provision_vm
from cfme.fixtures.cli import update_appliance
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.test_framework.sprout.client import AuthException
from cfme.test_framework.sprout.client import SproutClient
from cfme.utils.appliance import find_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.wait import wait_for

TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="pod appliance should be updated thru openshift mechanism")
]


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is split and minor_build is picked out for generating each version
    and appending it to the empty versions list"""
    versions = []
    version = find_appliance(metafunc).version

    split_ver = str(version).split(".")
    try:
        minor_build = split_ver[2]
        assert int(minor_build) != 0
    except IndexError:
        logger.exception('Caught IndexError generating for test_appliance_update, skipping')
    except AssertionError:
        logger.debug('Caught AssertionError: No previous z-stream version to update from')
        versions.append(
            pytest.param(
                "bad:{!r}".format(version),
                marks=pytest.mark.uncollect('Could not parse minor_build from: {}'.format(version))
            )
        )
    except Exception:  # diaper just in case
        logger.exception('Exception hit parsing version for test_appliance_update')
    metafunc.parametrize('old_version', versions, indirect=True)


@pytest.fixture
def old_version(request):
    return request.param


@pytest.fixture(scope="function", )
def appliance_preupdate(old_version, appliance):

    series = appliance.version.series()
    update_url = "update_url_{}".format(series.replace('.', ''))

    """Requests appliance from sprout based on old_versions, edits partitions and adds
    repo file for update"""

    usable = []
    sp = SproutClient.from_config(sprout_user_key=pytest.config.option.sprout_user_key or None)
    available_versions = set(sp.call_method('available_cfme_versions'))
    for a in available_versions:
        if a.startswith(old_version):
            usable.append(Version(a))
    usable.sort(reverse=True)
    try:
        apps, pool_id = sp.provision_appliances(count=1,
                                                preconfigured=True,
                                                lease_time=180,
                                                version=str(usable[0]))
    except AuthException:
        msg = ('Sprout credentials key or yaml maps missing or invalid,'
               'unable to provision appliance version %s for preupdate'.format(str(usable[0])))
        logger.exception(msg)
        pytest.skip(msg)

    apps[0].db.extend_partition()
    urls = cfme_data["basic_info"][update_url]
    apps[0].ssh_client.run_command(
        "curl {} -o /etc/yum.repos.d/update.repo".format(urls)
    )
    logger.info('Appliance update.repo file: \n%s',
                apps[0].ssh_client.run_command('cat /etc/yum.repos.d/update.repo').output)
    yield apps[0]
    apps[0].ssh_client.close()
    sp.destroy_pool(pool_id)


@pytest.mark.rhel_testing
def test_update_yum(appliance_preupdate, appliance):
    """Tests appliance update between versions

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    appliance_preupdate.evmserverd.stop()
    with appliance_preupdate.ssh_client as ssh:
        result = ssh.run_command('yum update -y', timeout=3600)
        assert result.success, "update failed {}".format(result.output)
    appliance_preupdate.evmserverd.start()
    appliance_preupdate.wait_for_web_ui()
    result = appliance_preupdate.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
    assert result.output in appliance.version


@pytest.mark.ignore_stream("upstream")
def test_update_webui(appliance_with_providers, appliance, request, old_version):
    """ Tests updating an appliance with providers, also confirms that the
        provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    update_appliance(appliance_with_providers)

    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_with_providers),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appliance_with_providers)
    vm = provision_vm(request, virtual_crud)
    assert vm.provider.mgmt.does_vm_exist(vm.name), "vm not provisioned"


@pytest.mark.ignore_stream("upstream")
def test_update_scap_webui(appliance_with_providers, appliance, request, old_version):
    """ Tests updating an appliance with providers and scap hardened, also confirms that the
        provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    appliance_with_providers.appliance_console.scap_harden_appliance()
    rules_failures = appliance_with_providers.appliance_console.scap_check_rules()
    assert not rules_failures, "Some rules have failed, check log"
    update_appliance(appliance_with_providers)

    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_with_providers),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    # Re-harden appliance and confirm rules are applied.
    rules_failures = appliance_with_providers.appliance_console.scap_check_rules()
    assert not rules_failures, "Some rules have failed, check log"
    # Verify that existing provider can detect new VMs on the second appliance
    virtual_crud = provider_app_crud(VMwareProvider, appliance_with_providers)
    vm = provision_vm(request, virtual_crud)
    assert vm.provider.mgmt.does_vm_exist(vm.name), "vm not provisioned"


@pytest.mark.ignore_stream("upstream")
def test_update_embedded_ansible_webui(enabled_embedded_appliance, appliance, old_version):
    """ Tests updating an appliance which has embedded ansible role enabled, also confirms that the
        role continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    update_appliance(enabled_embedded_appliance)
    wait_for(do_appliance_versions_match, func_args=(appliance, enabled_embedded_appliance),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running, num_sec=90)
    assert wait_for(func=lambda: enabled_embedded_appliance.rabbitmq_server.running, num_sec=60)
    assert wait_for(func=lambda: enabled_embedded_appliance.nginx.running, num_sec=60)
    repositories = enabled_embedded_appliance.collections.ansible_repositories
    name = "example_{}".format(fauxfactory.gen_alpha())
    description = "edited_{}".format(fauxfactory.gen_alpha())
    try:
        repository = repositories.create(
            name=name,
            url=cfme_data.ansible_links.playbook_repositories.console_db,
            description=description)
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
    view = navigate_to(repository, "Details")
    refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status").lower() == "successful",
        timeout=60,
        fail_func=refresh
    )


@pytest.mark.ignore_stream("upstream")
def test_update_distributed_webui(ext_appliances_with_providers, appliance, request, old_version,
                                  soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    update_appliance(ext_appliances_with_providers[0])
    wait_for(do_appliance_versions_match, func_args=(appliance, ext_appliances_with_providers[0]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    wait_for(do_appliance_versions_match, func_args=(appliance, ext_appliances_with_providers[1]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[0])
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[1])
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    soft_assert(vm1.provider.mgmt.does_vm_exist(vm1.name), "vm not provisioned")
    soft_assert(vm2.provider.mgmt.does_vm_exist(vm2.name), "vm not provisioned")


@pytest.mark.ignore_stream("upstream")
def test_update_replicated_webui(replicated_appliances_with_providers, appliance, request,
                                 old_version, soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    providers_before_upgrade = set(replicated_appliances_with_providers[0].managed_provider_names)
    update_appliance(replicated_appliances_with_providers[0])
    update_appliance(replicated_appliances_with_providers[1])
    wait_for(do_appliance_versions_match,
             func_args=(appliance, replicated_appliances_with_providers[0]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    wait_for(do_appliance_versions_match,
             func_args=(appliance, replicated_appliances_with_providers[1]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')

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
def test_update_ha_webui(ha_appliances_with_providers, appliance, request, old_version):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        initialEstimate: 1/4h
    """
    update_appliance(ha_appliances_with_providers[2])
    wait_for(do_appliance_versions_match, func_args=(appliance, ha_appliances_with_providers[2]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')
    # Cause failover to occur
    result = ha_appliances_with_providers[0].ssh_client.run_command(
        'systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
    assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    def is_failover_started():
        return ha_appliances_with_providers[2].ssh_client.run_command(
            "grep 'Starting to execute failover' /var/www/miq/vmdb/log/ha_admin.log").success

    wait_for(is_failover_started, timeout=450, handle_exception=True,
             message='Waiting for HA failover')
    ha_appliances_with_providers[2].wait_for_evm_service()
    ha_appliances_with_providers[2].wait_for_web_ui()
    # Verify that existing provider can detect new VMs
    virtual_crud = provider_app_crud(VMwareProvider, ha_appliances_with_providers[2])
    vm = provision_vm(request, virtual_crud)
    assert vm.provider.mgmt.does_vm_exist(vm.name), "vm not provisioned"
