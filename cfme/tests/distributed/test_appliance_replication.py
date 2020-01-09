from time import sleep
from urllib.parse import urlparse

import pytest
from wrapanapi import VmState

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient

pytestmark = [
    pytest.mark.long_running,
    test_requirements.distributed,
]


def get_ssh_client(hostname):
    """ Returns fresh ssh client connected to given server using given credentials
    """
    hostname = urlparse('scheme://' + hostname).netloc
    connect_kwargs = {
        'username': credentials['ssh']['username'],
        'password': credentials['ssh']['password'],
        'hostname': hostname,
    }
    return SSHClient(**connect_kwargs)


def configure_replication_appliances(appliances):
    """Configures two database-owning appliances, with unique region numbers,
    then sets up database replication between them.
    """
    remote_app, global_app = appliances

    remote_app.configure(region=0)
    remote_app.wait_for_web_ui()

    global_app.configure(region=99, key_address=remote_app.hostname)
    global_app.wait_for_web_ui()

    remote_app.set_pglogical_replication(replication_type=':remote')
    global_app.set_pglogical_replication(replication_type=':global')
    global_app.add_pglogical_replication_subscription(remote_app.hostname)


def configure_distributed_appliances(appliances):
    """Configures one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    appl1, appl2 = appliances
    appl1.configure(region=1)
    appl1.wait_for_web_ui()
    appl2.configure(region=1, key_address=appl1.hostname, db_address=appl1.hostname)
    appl2.wait_for_web_ui()


@pytest.fixture(scope="function")
def vm_obj(virtualcenter_provider):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm_name = random_vm_name('distpwr')
    collection = virtualcenter_provider.appliance.provider_based_collection(virtualcenter_provider)
    vm = collection.instantiate(vm_name, virtualcenter_provider)

    if not virtualcenter_provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %r on provider %r", vm_name, virtualcenter_provider.key)
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    else:
        logger.info("recycling deployed vm %r on provider %r", vm_name, virtualcenter_provider.key)

    vm.mgmt.ensure_state(VmState.RUNNING)

    yield vm

    vm.cleanup_on_provider()


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(
        virtualcenter_provider, temp_appliances_unconfig_funcscope_rhevm):
    """Tests that a provider added to an appliance in one region
        is replicated to the parent appliance in another region.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        virtualcenter_provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(
        virtualcenter_provider, temp_appliances_unconfig_funcscope_rhevm):
    """Tests that one appliance can be configured to connect to the database of another appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_distributed_appliances(temp_appliances_unconfig_funcscope_rhevm)

    appl1, appl2 = temp_appliances_unconfig_funcscope_rhevm
    appl1.browser_steal = True
    with appl1:
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.browser_steal = True
    with appl2:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection(
        virtualcenter_provider, temp_appliances_unconfig_funcscope_rhevm):
    """Tests a database disconnection

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    global_app.db_service.stop()
    sleep(60)
    global_app.db_service.start()

    remote_app.browser_steal = True
    with remote_app:
        virtualcenter_provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection_with_backlog(
        virtualcenter_provider, temp_appliances_unconfig_funcscope_rhevm):
    """Tests a database disconnection with backlog

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        # Replication is up and running, now stop the DB on the replication parent
        virtualcenter_provider.create()
        global_app.db_service.stop()
        sleep(60)
        global_app.db_service.start()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        global_app.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_distributed_vm_power_control(
        vm_obj, virtualcenter_provider, register_event, soft_assert,
        temp_appliances_unconfig_funcscope_rhevm):
    """Tests that a replication parent appliance can control the power state of a
    VM being managed by a replication child appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    configure_replication_appliances(temp_appliances_unconfig_funcscope_rhevm)
    remote_app, global_app = temp_appliances_unconfig_funcscope_rhevm

    remote_app.browser_steal = True
    with remote_app:
        virtualcenter_provider.create()
        remote_app.collections.infra_providers.wait_for_a_provider()

    global_app.browser_steal = True
    with global_app:
        register_event(target_type='VmOrTemplate', target_name=vm_obj.name,
                       event_type='request_vm_poweroff')
        register_event(target_type='VmOrTemplate', target_name=vm_obj.name,
                       event_type='vm_poweroff')

        vm_obj.power_control_from_cfme(option=vm_obj.POWER_OFF, cancel=False)
        navigate_to(vm_obj.provider, 'Details')
        vm_obj.wait_for_vm_state_change(desired_state=vm_obj.STATE_OFF, timeout=900)
        soft_assert(vm_obj.find_quadicon().data['state'] == 'off')
        soft_assert(
            not vm_obj.mgmt.is_running,
            "vm running")
