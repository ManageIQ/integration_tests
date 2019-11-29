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
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.version import get_stream
from cfme.utils.version import Version
from cfme.utils.wait import wait_for
from cfme.utils.wait import wait_for_decorator


TimedCommand = namedtuple('TimedCommand', ['command', 'timeout'])
pytestmark = [
    pytest.mark.uncollectif(lambda appliance: appliance.is_pod,
                            reason="pod appliance should be updated thru openshift mechanism")
]


def pytest_generate_tests(metafunc):
    """The following lines generate appliance versions based from the current build.
    Appliance version is split and z-version is picked out for generating each version
    and appending it to the empty versions list"""
    version = find_appliance(metafunc).version
    versions = []

    old_version_pytest_arg = metafunc.config.getoption('old_version')
    if old_version_pytest_arg == 'same':
        versions.append(version)
    elif old_version_pytest_arg is None:
        split_ver = str(version).split(".")
        try:
            z_version = int(split_ver[2])
        except (IndexError, ValueError) as e:
            logger.exception("Couldn't parse version: %s, skipping", e)
            versions.append(
                pytest.param(
                    f"bad:{version}",
                    marks=pytest.mark.uncollect(reason=f'Could not parse z_version from: {version}')
                )
            )
        else:
            z_version = z_version - 1
            if z_version < 0:
                reason_str = (f'No previous z-stream version to update from: {version}')
                logger.debug(reason_str)
                versions.append(
                    pytest.param(f"bad:{version}", marks=pytest.mark.uncollect(reason=reason_str))
                )
            else:
                versions.append(f"{split_ver[0]}.{split_ver[1]}.{z_version}")
    else:
        versions.append(old_version_pytest_arg)
    metafunc.parametrize('old_version', versions, indirect=True)


@pytest.fixture
def old_version(request):
    return request.param


@pytest.fixture(scope="function", )
def appliance_preupdate(old_version, appliance, request):

    series = appliance.version.series()
    update_url = "update_url_{}".format(series.replace('.', ''))

    """Requests appliance from sprout based on old_versions, edits partitions and adds
    repo file for update"""

    usable = []
    sprout = SproutClient.from_config(
        sprout_user_key=request.config.getoption('sprout_user_key', default=None) or None
    )
    available_versions = set(sprout.call_method('available_cfme_versions'))
    for a in available_versions:
        if a.startswith(old_version):
            usable.append(Version(a))
    usable.sort(reverse=True)
    try:
        apps, pool_id = sprout.provision_appliances(count=1,
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
    sprout.destroy_pool(pool_id)


def do_yum_update(appliance):
    appliance.evmserverd.stop()
    with appliance.ssh_client as ssh:
        result = ssh.run_command('yum update -y', timeout=3600)
        assert result.success, "update failed {}".format(result.output)
    appliance.evmserverd.start()
    appliance.wait_for_web_ui()


def test_update_yum(appliance_preupdate, appliance):
    """Tests appliance update between versions

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    do_yum_update(appliance_preupdate)
    result = appliance_preupdate.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
    assert result.output in appliance.version


@pytest.mark.ignore_stream("upstream")
def test_update_webui(appliance_with_providers, appliance, request, old_version):
    """ Tests updating an appliance with providers, also confirms that the
        provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    update_appliance(appliance_with_providers)

    wait_for(do_appliance_versions_match, func_args=(appliance, appliance_with_providers),
             num_sec=1200, delay=20, handle_exception=True,
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
        casecomponent: Appliance
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
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    update_appliance(enabled_embedded_appliance)
    with enabled_embedded_appliance:
        wait_for(do_appliance_versions_match, func_args=(appliance, enabled_embedded_appliance),
                num_sec=900, delay=20, handle_exception=True,
                message='Waiting for appliance to update')
    assert wait_for(func=lambda: enabled_embedded_appliance.is_embedded_ansible_running,
                    num_sec=180)
    assert wait_for(func=lambda: enabled_embedded_appliance.rabbitmq_server.running,
                    num_sec=60)
    assert wait_for(func=lambda: enabled_embedded_appliance.nginx.running,
                    num_sec=60)
    enabled_embedded_appliance.wait_for_web_ui()

    with enabled_embedded_appliance:
        repositories = enabled_embedded_appliance.collections.ansible_repositories
        name = fauxfactory.gen_alpha(15, start="example_")
        description = fauxfactory.gen_alpha(15, start="edited_")
        try:
            repository = repositories.create(
                name=name,
                url=cfme_data.ansible_links.playbook_repositories.console_db,
                description=description)
        except KeyError:
            pytest.skip("Skipping since no such key found in yaml")
        view = navigate_to(repository, "Details")
        refresh = view.toolbar.refresh.click

        @wait_for_decorator(timeout=60, fail_func=refresh)
        def success():
            properties = view.entities.summary("Properties")
            return properties.get_text_of("Status").lower() == "successful"


@pytest.mark.ignore_stream("upstream")
def test_update_distributed_webui(ext_appliances_with_providers, appliance,
        request, old_version, soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
    provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    update_appliance(ext_appliances_with_providers[0])
    for updated_appliance in ext_appliances_with_providers:
        wait_for(do_appliance_versions_match, func_args=(appliance, updated_appliance),
                num_sec=900, delay=20, handle_exception=True,
                message='Waiting for appliance to update')
        updated_appliance.evmserverd.wait_for_running()
        updated_appliance.wait_for_web_ui()

    # Verify that existing provider can detect new VMs on both apps
    virtual_crud_appl1 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[0])
    virtual_crud_appl2 = provider_app_crud(VMwareProvider, ext_appliances_with_providers[1])
    vm1 = provision_vm(request, virtual_crud_appl1)
    vm2 = provision_vm(request, virtual_crud_appl2)
    soft_assert(vm1.provider.mgmt.does_vm_exist(vm1.name), "vm not provisioned")
    soft_assert(vm2.provider.mgmt.does_vm_exist(vm2.name), "vm not provisioned")


@pytest.mark.ignore_stream("upstream")
def test_update_replicated_webui(get_replicated_appliances_with_providers, appliance, request,
                                 old_version, soft_assert):
    """ Tests updating an appliance with providers, also confirms that the
            provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    replicated_appliances_with_providers = get_replicated_appliances_with_providers
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
    replicated_appliances_with_providers[0].evmserverd.wait_for_running()
    replicated_appliances_with_providers[1].evmserverd.wait_for_running()
    replicated_appliances_with_providers[0].wait_for_web_ui()
    replicated_appliances_with_providers[1].wait_for_web_ui()

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
@pytest.mark.meta(coverage=[1704835])
@pytest.mark.parametrize("update_strategy", [update_appliance, do_yum_update], ids=["webui", "yum"])
def test_update_ha(ha_appliances_with_providers, appliance, update_strategy, request, old_version):
    """ Tests updating an appliance with providers using webui, also confirms that the
            provisioning continues to function correctly after the update has completed

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Appliance
        initialEstimate: 1/4h
    """
    evm_log = '/var/www/miq/vmdb/log/evm.log'
    update_strategy(ha_appliances_with_providers[2])
    wait_for(do_appliance_versions_match, func_args=(appliance, ha_appliances_with_providers[2]),
             num_sec=900, delay=20, handle_exception=True,
             message='Waiting for appliance to update')

    assert ha_appliances_with_providers[2].evm_failover_monitor.running

    with LogValidator(evm_log,
                      matched_patterns=['Starting to execute failover'],
                      hostname=ha_appliances_with_providers[2].hostname).waiting(wait=450):
        # Cause failover to occur
        result = ha_appliances_with_providers[0].ssh_client.run_command(
            'systemctl stop $APPLIANCE_PG_SERVICE', timeout=15)
        assert result.success, "Failed to stop APPLIANCE_PG_SERVICE: {}".format(result.output)

    ha_appliances_with_providers[2].evmserverd.wait_for_running()
    ha_appliances_with_providers[2].wait_for_web_ui()
    # Verify that existing provider can detect new VMs
    virtual_crud = provider_app_crud(VMwareProvider, ha_appliances_with_providers[2])
    vm = provision_vm(request, virtual_crud)
    assert vm.provider.mgmt.does_vm_exist(vm.name), "vm not provisioned"
