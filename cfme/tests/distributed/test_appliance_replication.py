# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest

import cfme.web_ui.flash as flash
from cfme.common.vm import VM
from cfme.configure import configuration as conf
from selenium.common.exceptions import WebDriverException
from cfme.infrastructure.provider import wait_for_a_provider
import cfme.fixtures.pytest_selenium as sel
from time import sleep
from urlparse import urlparse
from utils import db, version
from utils.appliance import provision_appliance
from utils.conf import credentials
from utils.log import logger
from utils.providers import setup_a_provider
from utils.ssh import SSHClient
from utils.wait import wait_for

pytestmark = [pytest.mark.long_running]


@pytest.fixture
def vmware_provider():
    return setup_a_provider(prov_class="infra", prov_type="virtualcenter")


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


# TODO: These calls here should not be separate functions, the functions should be on the appliance
# and we should be using the with context manager, they are being used incorrectly below
def stop_db_process(address):
    with get_ssh_client(address) as ssh:
        assert ssh.run_command('service {}-postgresql stop'.format(db.scl_name()))[0] == 0,\
            "Could not stop postgres process on {}".format(address)


def start_db_process(address):
    with get_ssh_client(address) as ssh:
        assert ssh.run_command('service {}-postgresql start'.format(db.scl_name()))[0] == 0,\
            "Could not start postgres process on {}".format(address)


def update_appliance_uuid(address):
    with get_ssh_client(address) as ssh:
        assert ssh.run_command('uuidgen > /var/www/miq/vmdb/GUID')[0] == 0,\
            "Could not update appliance's uuid on {}".format(address)


def get_replication_appliances():
    """Returns two database-owning appliances configured
       with unique region numbers.
    """
    ver_to_prov = str(version.current_version())
    appl1 = provision_appliance(ver_to_prov, 'long-test_repl_A')
    appl2 = provision_appliance(ver_to_prov, 'long-test_repl_B')
    appl1.configure(region=1)
    appl1.ipapp.wait_for_web_ui()
    update_appliance_uuid(appl2.address)
    appl2.configure(region=2, key_address=appl1.address)
    appl2.ipapp.wait_for_web_ui()
    return (appl1, appl2)


def get_distributed_appliances():
    """Returns one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    ver_to_prov = str(version.current_version())
    appl1 = provision_appliance(ver_to_prov, 'long-test_childDB_A')
    appl2 = provision_appliance(ver_to_prov, 'long-test_childDB_B')
    appl1.configure(region=1, patch_ajax_wait=False)
    appl1.ipapp.wait_for_web_ui()
    appl2.configure(region=1, patch_ajax_wait=False, key_address=appl1.address,
                    db_address=appl1.address)
    appl2.ipapp.wait_for_web_ui()
    return (appl1, appl2)


def configure_db_replication(db_address):
    """Enables the sync role and configures the appliance to replicate to
       the db_address specified. Then, it waits for the UI to show the replication
       as active and the backlog as empty.
    """
    conf.set_replication_worker_host(db_address)
    flash.assert_message_contain("Configuration settings saved for CFME Server")
    try:
        sel.force_navigate("cfg_settings_currentserver_server")
    except WebDriverException:
        sel.handle_alert()
        sel.force_navigate("cfg_settings_currentserver_server")
    conf.set_server_roles(database_synchronization=True)
    sel.force_navigate("cfg_diagnostics_region_replication")
    wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
             num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
    assert conf.get_replication_status()
    wait_for(lambda: conf.get_replication_backlog(navigate=False) == 0, fail_condition=False,
             num_sec=120, delay=10, fail_func=sel.refresh, message="get_replication_backlog")


@pytest.fixture(scope="module")
def vm_name():
    return "test_repl_pwrctl_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="module")
def test_vm(request, vmware_provider, vm_name):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = VM.factory(vm_name, vmware_provider)

    request.addfinalizer(vm.delete_from_provider)

    if not vmware_provider.mgmt.does_vm_exist(vm_name):
        logger.info("deploying %s on provider %s", vm_name, vmware_provider.key)
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm %s on provider %s", vm_name, vmware_provider.key)
    vm.provider.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(request, vmware_provider):
    """Tests that a provider added to an appliance in one region
        is replicated to the parent appliance in another region.

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        vmware_provider.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(request, vmware_provider):
    """Tests that one appliance can externally
       connect to the database of another appliance.

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_distributed_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        vmware_provider.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_sync_role_change(request, vmware_provider):
    """Tests that a role change is replicated

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        # Replication is up and running, now disable DB sync role
        conf.set_server_roles(database_synchronization=False)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=True,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        assert conf.get_replication_status()
        vmware_provider.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_sync_role_change_with_backlog(request, vmware_provider):
    """Tests that a role change is replicated with backlog

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        # Replication is up and running, now disable DB sync role
        vmware_provider.create()
        conf.set_server_roles(database_synchronization=False)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=True,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        assert conf.get_replication_status()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection(request, vmware_provider):
    """Tests a database disconnection

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        # Replication is up and running, now stop the DB on the replication parent
        stop_db_process(appl2.address)
        sleep(60)
        start_db_process(appl2.address)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        assert conf.get_replication_status()
        vmware_provider.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection_with_backlog(request, vmware_provider):
    """Tests a database disconnection with backlog

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        # Replication is up and running, now stop the DB on the replication parent
        vmware_provider.create()
        stop_db_process(appl2.address)
        sleep(60)
        start_db_process(appl2.address)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
        assert conf.get_replication_status()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert vmware_provider.exists


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_distributed_vm_power_control(request, test_vm, vmware_provider, verify_vm_running,
                                      register_event, soft_assert):
    """Tests that a replication parent appliance can control the power state of a
    VM being managed by a replication child appliance.

    Metadata:
        test_flag: replication
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.ipapp.browser_steal = True
    with appl1.ipapp:
        configure_db_replication(appl2.address)
        vmware_provider.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        register_event('VmOrTemplate', test_vm.name, ['request_vm_poweroff', 'vm_poweroff'])
        test_vm.power_control_from_cfme(option=test_vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider})
        test_vm.wait_for_vm_state_change(desired_state=test_vm.STATE_OFF, timeout=900)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-off')
        soft_assert(
            not test_vm.provider.mgmt.is_vm_running(test_vm.name),
            "vm running")
