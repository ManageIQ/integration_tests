# pylint: disable=C0103
# pylint: disable=W0613
# pylint: disable=R0913
# pylint: disable=E1101

import db
import pytest
from unittestzero import Assert
from utils.conf import cfme_data

pytestmark = [pytest.mark.destructive,
              pytest.mark.usefixtures("fetch_providers")]


#Global Variables to store RHEV and Vsphere host names.Note that the 'test_event_host'
#test relies on the 'test_delete_event_host' test to populate these variables',because of which
#'test_event_host' should be run after running 'test_delete_event_host'.
rhev_host = ""
vsphere_host = ""


@pytest.fixture
def delete_fx_provider_event(db_session, name):
    session = db_session
    session.query(db.EmEvent).filter(db.EmEvent.id.in_(session.query(db.EmEvent.id).
        join(db.ExtManagementSystem, db.EmEvent.ems_id == db.ExtManagementSystem.id).
        filter(db.ExtManagementSystem.name == name).subquery())).delete(False)
    session.commit()


def fetch_list(data):
    tests = []
    for provider in data["management_systems"]:
        prov_data = data['management_systems'][provider]
        if prov_data["type"] == 'virtualcenter' or \
                prov_data["type"] == 'rhevm':
            prov_type = prov_data["type"]
            if "test_vm_power_control" in prov_data:
                for vm_name in prov_data["test_vm_power_control"]:
                    tests.append(['', provider, vm_name, prov_type])

    return tests


def pytest_generate_tests(metafunc):
    argnames = []

    argnames = ['fetch_providers', 'provider', 'vm_name', 'prov_type']
    metafunc.parametrize(argnames, fetch_list(cfme_data), scope="module")


#Delete events for VM,host,provider and cluster using delete_fx* fixture and verify that the
#timelines button is inactive on the summary page of VM,host,provider,cluster
def test_delete_event_vm(
        provider, vm_name, prov_type, load_vm_details, db_session, verify_vm_running):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('on', 12)
    provider = vm_details_pg.provider_name
    delete_fx_provider_event(db_session, provider)
    vm_details_pg.refresh()
    Assert.true(vm_details_pg.inactive_timelines_button)


def test_delete_event_host(
        provider, vm_name, prov_type, load_vm_details, db_session, verify_vm_running):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('on', 12)
    global rhev_host, vsphere_host
    if prov_type == 'rhevm':
        rhev_host = vm_details_pg.host_name
    elif prov_type == 'virtualcenter':
        vsphere_host = vm_details_pg.host_name
    provider = vm_details_pg.provider_name
    delete_fx_provider_event(db_session, provider)
    host_details_pg = vm_details_pg.click_on_host_relationship_button()
    Assert.true(host_details_pg.inactive_timelines_button)


def test_delete_event_provider(
        provider, vm_name, prov_type, load_vm_details, db_session, verify_vm_running):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('on', 12)
    provider = vm_details_pg.provider_name
    delete_fx_provider_event(db_session, provider)
    provider_details_pg = vm_details_pg.click_on_provider_relationship_button()
    timelines_pg = provider_details_pg.click_on_timelines()
    Assert.true(timelines_pg.is_no_events_found)


def test_delete_event_cluster(
        provider, vm_name, prov_type, load_vm_details, db_session, verify_vm_running):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('on', 12)
    provider = vm_details_pg.provider_name
    delete_fx_provider_event(db_session, provider)
    cluster_details_pg = vm_details_pg.click_on_cluster_relationship_button()
    Assert.true(cluster_details_pg.inactive_timelines_button)


#Generate event by powering off the VM and then verify 1)that the timeline renders and 2)the power
#off event is displayed on the timelines page of VM,host,provider and cluster.
#Note that the unexpected error found check is to catch issues like the one reported in BZ1016686
def test_event_vm(provider, vm_name, prov_type, load_vm_details, verify_vm_stopped):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('off', 12)
    timelines_pg = vm_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if prov_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif prov_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


#This test should be run after running test_delete_event_host.
def test_event_host(
        provider, vm_name, prov_type, load_providers_host_list, verify_vm_stopped):
    host_list_pg = load_providers_host_list
    print provider, vm_name
    if prov_type == 'rhevm':
        host_details_pg = host_list_pg.click_host(rhev_host)
        timelines_pg = host_details_pg.click_on_timelines()
    elif prov_type == 'virtualcenter':
        host_details_pg = host_list_pg.click_host(vsphere_host)
        timelines_pg = host_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if prov_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif prov_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


def test_event_provider(provider, vm_name, prov_type, load_vm_details, verify_vm_stopped):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('off', 12)
    provider_details_pg = vm_details_pg.click_on_provider_relationship_button()
    timelines_pg = provider_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if prov_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif prov_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)


def test_event_cluster(provider, vm_name, prov_type, load_vm_details, verify_vm_stopped):
    vm_details_pg = load_vm_details
    vm_details_pg.wait_for_vm_state_change('off', 12)
    cluster_details_pg = vm_details_pg.click_on_cluster_relationship_button()
    timelines_pg = cluster_details_pg.click_on_timelines()
    Assert.false(timelines_pg.is_unexpected_error_found)
    Assert.true(timelines_pg.vm_event_found(vm_name))
    if prov_type == 'rhevm':
        Assert.true(timelines_pg.rhev_vm_event_img_found)
    elif prov_type == 'virtualcenter':
        Assert.true(timelines_pg.vsphere_vm_event_img_found)
