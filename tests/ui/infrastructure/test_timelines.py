# pylint: disable=C0103
# pylint: disable=W0613
# pylint: disable=R0913
# pylint: disable=E1101

import pytest
from fixtures import navigation as nav
from unittestzero import Assert
from utils.conf import cfme_data

pytestmark = [pytest.mark.usefixtures("setup_infrastructure_providers"),
              pytest.mark.usefixtures("fetch_providers"),
              pytest.mark.usefixtures("get_host_name"),
              pytest.mark.usefixtures("delete_fx_provider_event"),
              pytest.mark.usefixtures("verify_vm_stopped")]


#Global Variable to store RHEV/Vsphere host name.
host = ""


@pytest.fixture(scope="module")
def delete_fx_provider_event(db, provider_name):
    ems = db['ext_management_systems']
    ems_events = db['ems_events']
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider_name)
        )
        db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery())).delete(False)


def fetch_list(data):
    tests = []

    for provider in data["management_systems"]:
        prov_data = data['management_systems'][provider]
        if prov_data["type"] == 'virtualcenter' or \
                prov_data["type"] == 'rhevm':
            provider_type = prov_data["type"]
            provider_name = prov_data["name"]
            if "test_vm_power_control" in prov_data:
                for vm_name in prov_data["test_vm_power_control"]:
                    tests.append(['', provider, vm_name, provider_type, provider_name])

    return tests


def pytest_generate_tests(metafunc):
    argnames = ['fetch_providers', 'provider', 'vm_name', 'provider_type', 'provider_name']
    metafunc.parametrize(argnames, fetch_list(cfme_data), scope="module")


@pytest.fixture(scope="module")
def power_on_vm(mgmt_sys_api_clients, provider, vm_name):
    mgmt_sys_api_clients[provider].wait_vm_steady(vm_name)
    mgmt_sys_api_clients[provider].start_vm(vm_name)


def nav_to_vm_details(provider, vm_name):
    '''Helper nav function to get to vm details and avoid unneccessary navigation'''

    provider_details = nav.infra_providers_pg().load_provider_details(
        cfme_data["management_systems"][provider]["name"])
    return provider_details.all_vms().find_vm_page(vm_name, None, False, True, 6)


@pytest.fixture(scope="module")
def get_host_name(power_on_vm, provider, vm_name, provider_type):
    '''Get host name from VM details page after powering on VM

    For a RHEV VM,RHEV host name shows up on the VM details page only when the VM is running.
    '''
    vm_details_pg = nav_to_vm_details(provider, vm_name)
    vm_details_pg.wait_for_vm_state_change('on', 12)
    global host
    host = vm_details_pg.host_name


#Generate event by powering off the VM and then verify 1)that the timeline is rendered properly
#and 2)the power off event is displayed on the timelines page of VM,host,provider and cluster.
#Note that the unexpected error found check is to catch issues like the one reported in BZ1016686
def test_event_vm(
        provider, vm_name, provider_type, provider_name, load_vm_details):
    load_vm_details.wait_for_vm_state_change('off', 12)
    load_vm_details.refresh()
    timelines_pg = load_vm_details.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if provider_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif provider_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


def test_event_host(
        provider, vm_name, provider_type, provider_name, load_providers_host_list):
    host_details_pg = load_providers_host_list.click_host(host)
    timelines_pg = host_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if provider_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif provider_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


def test_event_provider(
        provider, vm_name, provider_type, provider_name, load_vm_details):
    load_vm_details.wait_for_vm_state_change('off', 12)
    provider_details_pg = load_vm_details.click_on_provider_relationship_button()
    timelines_pg = provider_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if provider_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif provider_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


def test_event_cluster(
        provider, vm_name, provider_type, provider_name, load_vm_details):
    load_vm_details.wait_for_vm_state_change('off', 12)
    cluster_details_pg = load_vm_details.click_on_cluster_relationship_button()
    timelines_pg = cluster_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if provider_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif provider_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)
