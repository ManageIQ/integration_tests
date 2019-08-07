# -*- coding: utf-8 -*-
from time import sleep
from urllib.parse import urlparse

import pytest

from cfme import test_requirements
from cfme.base.ui import ServerView
from cfme.utils.appliance import provision_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    test_requirements.distributed,
    # TODO: refactor to use appliance fixtures that use sprout
    pytest.mark.uncollect(reason="test framework broke browser_steal"),
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


def get_replication_appliances(appliance):
    """Returns two database-owning appliances configured
       with unique region numbers.
    """
    ver_to_prov = str(appliance.version)
    # FIXME: refactor to use appliance fixtures that use sprout, or pass provider name
    appl1 = provision_appliance(ver_to_prov, 'long-test_repl_A')
    appl2 = provision_appliance(ver_to_prov, 'long-test_repl_B')
    appl1.configure(region=1)
    appl1.ipapp.wait_for_web_ui()
    appl2.update_guid()
    appl2.configure(region=2, key_address=appl1.hostname)
    appl2.ipapp.wait_for_web_ui()
    return appl1, appl2


def get_distributed_appliances(appliance):
    """Returns one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    ver_to_prov = str(appliance.version)
    appl1 = provision_appliance(ver_to_prov, 'long-test_childDB_A')
    appl2 = provision_appliance(ver_to_prov, 'long-test_childDB_B')
    appl1.configure(region=1)
    appl1.ipapp.wait_for_web_ui()
    appl2.configure(region=1, key_address=appl1.hostname, db_address=appl1.hostname)
    appl2.ipapp.wait_for_web_ui()
    return appl1, appl2


def configure_db_replication(db_address, appliance):
    """Enables the sync role and configures the appliance to replicate to
       the db_address specified. Then, it waits for the UI to show the replication
       as active and the backlog as empty.
    """
    replication_conf = appliance.server.zone.region.replication
    replication_conf.set_replication(
        {'host': db_address}, 'global')
    view = appliance.server.browser.create_view(ServerView)
    view.flash.assert_message("Configuration settings saved for CFME Server")  # may be partial
    appliance.server.settings.enable_server_roles('database_synchronization')
    rep_status, _ = wait_for(replication_conf.get_replication_status, fail_condition=False,
                             num_sec=360, delay=10,
                             fail_func=appliance.server.browser.refresh,
                             message="get_replication_status")
    assert rep_status
    wait_for(lambda: replication_conf.get_global_replication_backlog == 0, fail_condition=False,
             num_sec=120, delay=10,
             fail_func=appliance.server.browser.refresh, message="get_replication_backlog")


@pytest.fixture(scope="module")
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
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(request, virtualcenter_provider):
    """Tests that a provider added to an appliance in one region
        is replicated to the parent appliance in another region.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.hostname)
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(request, virtualcenter_provider, appliance):
    """Tests that one appliance can externally
       connect to the database of another appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_distributed_appliances(appliance)

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_sync_role_change(request, virtualcenter_provider, appliance):
    """Tests that a role change is replicated

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()
    replication_conf = appliance.server.zone.region.replication

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        server_settings = appliance.server.settings
        configure_db_replication(appl2.hostname)
        # Replication is up and running, now disable DB sync role
        server_settings.disable_server_roles('database_synchronization')
        wait_for(replication_conf.get_replication_status, fail_condition=True, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        server_settings.enable_server_roles('database_synchronization')
        wait_for(replication_conf.get_replication_status, fail_condition=False, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        assert replication_conf.get_replication_status()
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream", "5.7")  # no config->diagnostics->replication tab in 5.7
def test_appliance_replicate_sync_role_change_with_backlog(request, virtualcenter_provider,
                                                           appliance):
    """Tests that a role change is replicated with backlog

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()
    replication_conf = appliance.server.zone.region.replication

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        server_settings = appliance.server.settings
        configure_db_replication(appl2.hostname)
        # Replication is up and running, now disable DB sync role
        virtualcenter_provider.create()
        server_settings.disable_server_roles('database_synchronization')
        wait_for(replication_conf.get_replication_status, fail_condition=True, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        server_settings.enable_server_roles('database_synchronization')
        wait_for(replication_conf.get_replication_status, fail_condition=False, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        assert replication_conf.get_replication_status()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream", "5.7")  # no config->diagnostics->replication tab in 5.7
def test_appliance_replicate_database_disconnection(request, virtualcenter_provider, appliance):
    """Tests a database disconnection

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()
    replication_conf = appliance.server.zone.region.replication

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.hostname)
        # Replication is up and running, now stop the DB on the replication parent
        appl2.db_service.stop()
        sleep(60)
        appl2.db_service.start()
        wait_for(replication_conf.get_replication_status, fail_condition=False, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        assert replication_conf.get_replication_status()
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream", "5.7")  # no config->diagnostics->replication tab in 5.7
def test_appliance_replicate_database_disconnection_with_backlog(request, virtualcenter_provider,
                                                                 appliance):
    """Tests a database disconnection with backlog

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()
    replication_conf = appliance.server.zone.region.replication

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.hostname)
        # Replication is up and running, now stop the DB on the replication parent
        virtualcenter_provider.create()
        appl2.db_service.stop()
        sleep(60)
        appl2.db_service.start()
        wait_for(replication_conf.get_replication_status, fail_condition=False, num_sec=360,
                 delay=10, fail_func=appl1.server.browser.refresh, message="get_replication_status")
        assert replication_conf.get_replication_status()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        appl2.collections.infra_providers.wait_for_a_provider()
        assert virtualcenter_provider.exists


@pytest.mark.rhel_testing
@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream", "5.7")  # no config->diagnostics->replication tab in 5.7
def test_distributed_vm_power_control(request, vm_obj, virtualcenter_provider, ensure_vm_running,
                                      register_event, soft_assert):
    """Tests that a replication parent appliance can control the power state of a
    VM being managed by a replication child appliance.

    Metadata:
        test_flag: replication

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: Appliance
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.hostname)
        virtualcenter_provider.create()
        appl1.collections.infra_providers.wait_for_a_provider()

    appl2.ipapp.browser_steal = True

    with appl2.ipapp:
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
