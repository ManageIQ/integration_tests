import pytest
import random

import cfme.web_ui.flash as flash
from cfme.configure import configuration as conf
from cfme.infrastructure.provider import wait_for_a_provider
import cfme.fixtures.pytest_selenium as sel
from utils import testgen
from utils.appliance import provision_appliance
from utils.conf import cfme_data
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


@pytest.mark.usefixtures("random_provider")
@pytest.mark.downstream
@pytest.mark.long_running
def test_appliance_replicate_between_regions(request, provider_crud):
    """Tests that a provider added to an appliance in one region
        is replicated to the parent appliance in another region.
    """
    appliance_data = cfme_data['appliance_provisioning']['single_appliance']
    appl1 = provision_appliance(appliance_data['version'], appliance_data['name'])
    appl2 = provision_appliance(appliance_data['version'], appliance_data['name'])

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.configure(region=1, patch_ajax_wait=False)
    appl2.configure(region=2, patch_ajax_wait=False, key_address=appl1.address)
    appl1.ipapp.wait_for_web_ui()
    with appl1.browser_session():
        conf.set_replication_worker_host(appl2.address)
        flash.assert_message_contain("Configuration settings saved for CFME Server")
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        wait_for(lambda: conf.get_replication_backlog(navigate=False) == 0, fail_condition=False,
                 num_sec=120, delay=10, fail_func=sel.refresh)
        provider_crud.create()
        wait_for_a_provider()

    with appl2.browser_session():
        wait_for_a_provider()
        assert provider_crud.exists


@pytest.mark.usefixtures("random_provider")
def test_appliance_replicate_sync_role_change(request, provider_crud):
    appliance_data = cfme_data['appliance_provisioning']['single_appliance']
    appl1 = provision_appliance(appliance_data['version'], appliance_data['name'])
    appl2 = provision_appliance(appliance_data['version'], appliance_data['name'])

    def finalize():
        appl1.destroy()
        appl2.destroy()
    request.addfinalizer(finalize)
    appl1.configure(region=1, patch_ajax_wait=False)
    appl2.configure(region=2, patch_ajax_wait=False)
    with appl1.browser_session():
        conf.set_replication_worker_host(appl2.address)
        flash.assert_message_contain("Configuration settings saved for CFME Server")
        conf.set_server_roles(database_synchronization=True)
        sel.force_navigate("cfg_diagnostics_region_replication")
        wait_for(lambda: conf.get_replication_status(navigate=False), fail_condition=False,
                 num_sec=360, delay=10, fail_func=sel.refresh)
        assert conf.get_replication_status()
        wait_for(lambda: conf.get_replication_backlog(navigate=False) == 0, fail_condition=False,
                 num_sec=120, delay=10, fail_func=sel.refresh)
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
        # provider_crud.create()
        # wait_for_a_provider()
