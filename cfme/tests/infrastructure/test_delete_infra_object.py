# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import pytest
from cfme.common.vm import VM
from cfme.infrastructure import host, datastore, cluster, resource_pool
from cfme.web_ui import Region
from utils import testgen

pytestmark = [pytest.mark.tier(3)]

details_page = Region(infoblock_type='detail')


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)

    argnames.append('remove_test')
    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if 'remove_test' not in args['provider'].data:
            # No provisioning data available
            continue

        new_idlist.append(idlist[i])
        argvalues[i].append(args['provider'].data['remove_test'])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def test_delete_cluster(setup_provider, provider, remove_test):
    """ Tests delete cluster

    Metadata:
        test_flag: delete_object
    """
    cluster_name = remove_test['cluster']
    test_cluster = cluster.Cluster(name=cluster_name)
    test_cluster.delete(cancel=False)
    test_cluster.wait_for_delete()
    provider.refresh_provider_relationships()
    test_cluster.wait_for_appear()


def test_delete_host(setup_provider, provider, remove_test):
    """ Tests delete host

    Metadata:
        test_flag: delete_object
    """
    host_name = remove_test['host']
    test_host = host.Host(name=host_name)
    test_host.delete(cancel=False)
    host.wait_for_host_delete(test_host)
    provider.refresh_provider_relationships()
    host.wait_for_host_to_appear(test_host)


def test_delete_vm(setup_provider, provider, remove_test):
    """ Tests delete vm

    Metadata:
        test_flag: delete_object
    """
    vm = remove_test['vm']
    test_vm = VM.factory(vm, provider)
    test_vm.delete()
    test_vm.wait_for_delete()
    provider.refresh_provider_relationships()
    test_vm.wait_to_appear()


def test_delete_template(setup_provider, provider, remove_test):
    """ Tests delete template

    Metadata:
        test_flag: delete_object
    """
    template = remove_test['template']
    test_template = VM.factory(template, provider, template=True)
    test_template.delete()
    test_template.wait_for_delete()
    provider.refresh_provider_relationships()
    test_template.wait_to_appear()


def test_delete_resource_pool(setup_provider, provider, remove_test):
    """ Tests delete pool

    Metadata:
        test_flag: delete_object
    """
    resourcepool_name = remove_test['resource_pool']
    test_resourcepool = resource_pool.ResourcePool(name=resourcepool_name)
    test_resourcepool.delete(cancel=False)
    test_resourcepool.wait_for_delete()
    provider.refresh_provider_relationships()
    test_resourcepool.wait_for_appear()


@pytest.mark.meta(blockers=[1236977])
@pytest.mark.ignore_stream("upstream")
def test_delete_datastore(setup_provider, provider, remove_test):
    """ Tests delete datastore

    Metadata:
        test_flag: delete_object
    """
    data_store = remove_test['datastore']
    test_datastore = datastore.Datastore(name=data_store)
    host_count = len(test_datastore.get_hosts())
    vm_count = len(test_datastore.get_vms())
    if host_count != 0:
        test_datastore.delete_all_attached_hosts()
        test_datastore.wait_for_delete_all()
    if vm_count != 0:
        test_datastore.delete_all_attached_vms()
        test_datastore.wait_for_delete_all()
    test_datastore.delete(cancel=False)
    test_datastore.wait_for_delete()
    provider.refresh_provider_relationships()
    test_datastore.wait_for_appear()
