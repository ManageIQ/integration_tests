# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import random

import cfme.web_ui.flash as flash
from cfme.configure import configuration as conf
from selenium.common.exceptions import UnexpectedAlertPresentException
from cfme.infrastructure.provider import wait_for_a_provider
from cfme.infrastructure.virtual_machines import Vm
import cfme.fixtures.pytest_selenium as sel
from time import sleep
from urlparse import urlparse
from utils import testgen, version
from utils.appliance import provision_appliance
from utils.conf import credentials
from utils.log import logger
from utils.ssh import SSHClient
from utils.providers import setup_provider
from utils.wait import wait_for

pytestmark = [pytest.mark.long_running]

pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")

random_vm_test = []


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], choose_random=True)
    if not idlist:
        return
    new_idlist = []
    new_argvalues = []
    if 'random_pwr_ctl_vm' in metafunc.fixturenames:
        if random_vm_test:
            argnames, new_argvalues, new_idlist = random_vm_test
        else:
            single_index = random.choice(range(len(idlist)))
            new_idlist = ['random_provider']
            new_argvalues = argvalues[single_index]
            argnames.append('random_pwr_ctl_vm')
            new_argvalues.append('')
            new_argvalues = [new_argvalues]
            random_vm_test.append(argnames)
            random_vm_test.append(new_argvalues)
            random_vm_test.append(new_idlist)
    else:
        new_idlist = idlist
        new_argvalues = argvalues
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


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


def stop_db_process(address):
    with get_ssh_client(address) as ssh:
        assert ssh.run_command('service postgresql92-postgresql stop')[0] == 0,\
            "Could not stop postgres process on {}".format(address)


def start_db_process(address):
    with get_ssh_client(address) as ssh:
        assert ssh.run_command('service postgresql92-postgresql start')[0] == 0,\
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
    appl1 = provision_appliance(ver_to_prov, 'test_repl_A')
    appl2 = provision_appliance(ver_to_prov, 'test_repl_B')
    appl1.configure(region=1, patch_ajax_wait=False)
    appl1.ipapp.wait_for_web_ui()
    update_appliance_uuid(appl2.address)
    appl2.configure(region=2, patch_ajax_wait=False, key_address=appl1.address)
    appl2.ipapp.wait_for_web_ui()
    return (appl1, appl2)


def get_distributed_appliances():
    """Returns one database-owning appliance, and a second appliance
       that connects to the database of the first.
    """
    ver_to_prov = str(version.current_version())
    appl1 = provision_appliance(ver_to_prov, 'test_childDB_A')
    appl2 = provision_appliance(ver_to_prov, 'test_childDB_B')
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
    except UnexpectedAlertPresentException:
        sel.handle_alert()
        sel.force_navigate("cfg_settings_currentserver_server")
    conf.set_server_roles(database_synchronization=True)
    sel.force_navigate("cfg_diagnostics_region_replication")
    wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
             num_sec=360, delay=10, fail_func=sel.refresh, message="get_replication_status")
    assert conf.get_replication_status()
    wait_for(lambda: conf.get_replication_backlog(navigate=False) == 0, fail_condition=False,
             num_sec=120, delay=10, fail_func=sel.refresh, message="get_replication_backlog")


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="module")
def vm_name():
    return "test_repl_pwrctl_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="class")
def test_vm(request, provider_crud, provider_mgmt, vm_name):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm = Vm(vm_name, provider_crud)

    request.addfinalizer(vm.delete_from_provider)

    if not provider_mgmt.does_vm_exist(vm_name):
        logger.info("deploying {} on provider {}".format(vm_name, provider_crud.key))
        vm.create_on_provider(allow_skip="default")
    else:
        logger.info("recycling deployed vm {} on provider {}".format(vm_name, provider_crud.key))
    vm.provider_crud.refresh_provider_relationships()
    vm.wait_to_appear()
    return vm


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_between_regions(request, provider_crud):
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
        provider_crud.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.ignore_stream("upstream")
def test_external_database_appliance(request, provider_crud):
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
        provider_crud.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_sync_role_change(request, provider_crud):
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
        provider_crud.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_sync_role_change_with_backlog(request, provider_crud):
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
        provider_crud.create()
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
        assert provider_crud.exists


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection(request, provider_crud):
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
        provider_crud.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.ignore_stream("upstream")
def test_appliance_replicate_database_disconnection_with_backlog(request, provider_crud):
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
        provider_crud.create()
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
        assert provider_crud.exists


@pytest.mark.usefixtures("random_pwr_ctl_vm")
@pytest.mark.usefixtures("provider_init")
@pytest.mark.ignore_stream("upstream")
def test_distributed_vm_power_control(request, test_vm, provider_crud,
                                      verify_vm_running, register_event, soft_assert):
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
        provider_crud.create()
        wait_for_a_provider()

    appl2.ipapp.browser_steal = True
    with appl2.ipapp:
        register_event(
            test_vm.provider_crud.get_yaml_data()['type'],
            "vm", test_vm.name, ["vm_power_off_req", "vm_power_off"])
        test_vm.power_control_from_cfme(option=Vm.POWER_OFF, cancel=False)
        flash.assert_message_contain("Stop initiated")
        pytest.sel.force_navigate(
            'infrastructure_provider', context={'provider': test_vm.provider_crud})
        test_vm.wait_for_vm_state_change(desired_state=Vm.STATE_OFF, timeout=900)
        soft_assert(test_vm.find_quadicon().state == 'currentstate-off')
        soft_assert(
            not test_vm.provider_crud.get_mgmt_system().is_vm_running(test_vm.name),
            "vm running")
