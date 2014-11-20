# -*- coding: utf-8 -*-

from cfme.exceptions import CandidateNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host, datastore, cluster, resource_pool, virtual_machines
from cfme.web_ui import Region, flash, Quadicon, toolbar as tb, paginator as pg
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
import pytest


details_page = Region(infoblock_type='detail')

pytestmark = [pytest.mark.usefixtures("setup_infrastructure_providers")]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'remove_test')

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['remove_test']:
            # No provisioning data available
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def test_delete_cluster(provider_crud, remove_test):
    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    test_cluster = cluster.Cluster(name=cluster_name)
    test_cluster.delete(cancel=False)
    flash.assert_message_contain('The selected Cluster was deleted')
    test_cluster.wait_for_delete()
    logger.info('Cluster {} disappeared after deletion'.format(cluster))
    provider_crud.refresh_provider_relationships()
    test_cluster.wait_for_appear()
    logger.info('Cluster {} appeared back after deletion'.format(cluster))


def test_delete_host(provider_crud, remove_test):
    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    test_host = host.Host(name=host_name)
    test_host.delete(cancel=False)
    flash.assert_message_match('The selected Host was deleted')
    host.wait_for_host_delete(test_host)
    logger.info('Host {} disappeared after deletion'.format(host_name))
    provider_crud.refresh_provider_relationships()
    host.wait_for_host_to_appear(test_host)
    logger.info('Host {} reappeared after deletion'.format(host_name))


def test_delete_vm(provider_crud, remove_test):
    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    test_vm = virtual_machines.Vm(vm, provider_crud)
    quad = Quadicon(vm, 'vm')
    test_vm.remove_from_cfme(cancel=False)
    flash.assert_message_contain(
        'Deletion initiated for 1 VM and Instance from the CFME Database')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait vm to disappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Vm {} disappeared after deletion'.format(vm))
    provider_crud.refresh_provider_relationships()
    sel.click(details_page.infoblock.element("Relationships", "VMs"))
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait template to appear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Vm {} reappeared after deletion'.format(vm))


def test_delete_template(provider_crud, remove_test):
    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    sel.force_navigate(
        'infrastructure_provider', context={'provider': provider_crud})
    sel.click(details_page.infoblock.element("Relationships", "Templates"))
    tb.select('Grid View')
    quad = Quadicon(template, 'template')
    if sel.is_displayed(quad):
        sel.check(quad.checkbox())
    tb.select('Configuration', 'Remove Templates from the VMDB', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain(
        'Deletion initiated for 1 VM Template and Image from the CFME Database')
    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait template to disappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Template {} disappeared after deletion'.format(template))
    provider_crud.refresh_provider_relationships()
    sel.click(details_page.infoblock.element("Relationships", "Templates"))
    tb.select('Grid View')
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait template to appear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Template {} reappeared after deletion'.format(template))


def test_delete_resource_pool(provider_crud, remove_test):
    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    test_resourcepool = resource_pool.ResourcePool(name=resourcepool_name)
    test_resourcepool.delete(cancel=False)
    flash.assert_message_contain('The selected Resource Pool was deleted')
    test_resourcepool.wait_for_delete()
    logger.info('Resource pool {} disappeared after deletion'.format(resource_pool))
    provider_crud.refresh_provider_relationships()
    test_resourcepool.wait_for_appear()
    logger.info('Resourcepool {} appeared back after deletion'.format(resource_pool))


def test_delete_datastore(provider_crud, remove_test):
    def delete_all_attached_hosts():
        sel.force_navigate('infrastructure_datastores')
        sel.click(quad)
        sel.click(details_page.infoblock.element("Relationships", "Managed VMs"))
        sel.click(pg.check_all())
        tb.select("Configuration", "Remove selected items from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def delete_all_attached_vms():
        sel.force_navigate('infrastructure_datastores')
        sel.click(quad)
        sel.click(details_page.infoblock.element("Relationships", "Hosts"))
        sel.click(pg.check_all())
        tb.select("Configuration", "Remove Hosts from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel=False)

    def wait_for_delete_all():
        try:
            sel.refresh()
            if sel.is_displayed_text("No Records Found"):
                return True
        except CandidateNotFound:
                return False

    cluster_name, host_name, vm, template, resourcepool_name, data_store = map(remove_test.get,
        ('cluster', 'host', 'vm', 'template', 'resource_pool', 'datastore'))
    sel.force_navigate('infrastructure_datastores')
    test_datastore = datastore.Datastore(name=data_store)
    quad = Quadicon(data_store, 'datastore')
    host_count = test_datastore.get_hosts()
    vm_count = test_datastore.get_vms()
    if len(host_count) == 0 and len(vm_count) == 0:
        test_datastore.delete(cancel=False)
    else:
        delete_all_attached_hosts()
        wait_for_delete_all()
        delete_all_attached_vms()
        wait_for_delete_all()
        test_datastore.delete(cancel=False)

    wait_for(lambda: not sel.is_displayed(quad), fail_condition=False,
             message="Wait datastore to disappear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Datastore {} disappeared after deletion'.format(data_store))
    provider_crud.refresh_provider_relationships()
    sel.force_navigate('infrastructure_datastores')
    wait_for(sel.is_displayed, func_args=[quad], fail_condition=False,
             message="Wait datastore to appear", num_sec=1000, fail_func=sel.refresh)
    logger.info('Datastore {} reappeared after deletion'.format(data_store))
