import pytest
import random

import cfme.web_ui.flash as flash
from cfme.configure import configuration as conf
from cfme.infrastructure.provider import wait_for_a_provider
import cfme.fixtures.pytest_selenium as sel
from time import sleep
from urlparse import urlparse
from utils import testgen
from utils.appliance import provision_appliance
from utils.conf import cfme_data, credentials
from utils.ssh import SSHClient
from utils.wait import wait_for

pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")

random_provider = []


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    if not idlist:
        return
    new_idlist = []
    new_argvalues = []
    if 'random_provider' in metafunc.fixturenames:
        if random_provider:
            argnames, new_argvalues, new_idlist = random_provider
        else:
            single_index = random.choice(range(len(idlist)))
            new_idlist = ['random_provider']
            new_argvalues = argvalues[single_index]
            argnames.append('random_provider')
            new_argvalues.append('')
            new_argvalues = [new_argvalues]
            random_provider.append(argnames)
            random_provider.append(new_argvalues)
            random_provider.append(new_idlist)
    else:
        new_idlist = idlist
        new_argvalues = argvalues
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


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


def get_replication_appliances():
    """Returns two database-owning appliances configured
       with unique region numbers.
    """
    appliance_data = cfme_data['appliance_provisioning']['single_appliance']
    appl1 = provision_appliance(appliance_data['version'], appliance_data['name'])
    appl2 = provision_appliance(appliance_data['version'], appliance_data['name'])
    appl1.configure(region=1, patch_ajax_wait=False)
    appl2.configure(region=2, patch_ajax_wait=False)
    return (appl1, appl2)


def configure_db_replication(db_address):
    """Enables the sync role and configures the appliance to replicate to
       the db_address specified. Then, it waits for the UI to show the replication
       as active and the backlog as empty.
    """
    conf.set_replication_worker_host(db_address)
    flash.assert_message_contain("Configuration settings saved for CFME Server")
    conf.set_server_roles(database_synchronization=True)
    sel.force_navigate("cfg_diagnostics_region_replication")
    wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
        num_sec=360, delay=10, fail_func=sel.refresh)
    assert conf.get_replication_status()
    wait_for(lambda: conf.get_replication_backlog(navigate=False) == 0, fail_condition=False,
        num_sec=120, delay=10, fail_func=sel.refresh)


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_between_regions(request, provider_crud):
    """Tests that a provider added to an appliance in one region
        is replicated to the parent appliance in another region.
    """
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    with appl1.browser_session():
        configure_db_replication(appl2.address)
        provider_crud.create()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_sync_role_change(request, provider_crud):
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    with appl1.browser_session():
        configure_db_replication(appl2.address)
        # Replication is up and running, now disable DB sync role
        conf.set_server_roles(database_synchronization=False)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=True,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        provider_crud.create()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_sync_role_change_with_backlog(request, provider_crud):
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    with appl1.browser_session():
        configure_db_replication(appl2.address)
        # Replication is up and running, now disable DB sync role
        provider_crud.create()
        conf.set_server_roles(database_synchronization=False)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=True,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_database_disconnection(request, provider_crud):
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    with appl1.browser_session():
        configure_db_replication(appl2.address)
        # Replication is up and running, now stop the DB on the replication parent
        stop_db_process(appl2.address)
        sleep(60)
        start_db_process(appl2.address)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        provider_crud.create()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_database_disconnection_with_backlog(request, provider_crud):
    appl1, appl2 = get_replication_appliances()

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    with appl1.browser_session():
        configure_db_replication(appl2.address)
        # Replication is up and running, now stop the DB on the replication parent
        provider_crud.create()
        stop_db_process(appl2.address)
        sleep(60)
        start_db_process(appl2.address)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists
