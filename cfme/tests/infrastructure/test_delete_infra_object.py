# -*- coding: utf-8 -*-

import pytest
from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure import host, datastore, resource_pool
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [pytest.mark.tier(3),
              test_requirements.general_ui]


pytest_generate_tests = testgen.generate(
    [InfraProvider], required_fields=['remove_test'], scope="module")


def test_delete_cluster_appear_after_refresh(setup_provider, provider, appliance):
    """ Tests delete cluster

    Metadata:
        test_flag: delete_object
    """
    cluster_name = provider.data['remove_test']['cluster']
    cluster_col = appliance.collections.clusters
    test_cluster = cluster_col.instantiate(name=cluster_name, provider=provider)
    test_cluster.delete(cancel=False, wait=True)
    provider.refresh_provider_relationships()
    test_cluster.wait_for_exists()


def test_delete_host_appear_after_refresh(appliance, setup_provider, provider):
    """ Tests delete host

    Metadata:
        test_flag: delete_object
    """
    host_collection = appliance.collections.hosts
    host_name = provider.data['remove_test']['host']
    test_host = host_collection.instantiate(name=host_name, provider=provider)
    test_host.delete(cancel=False)
    test_host.wait_for_delete()
    provider.refresh_provider_relationships()
    test_host.wait_to_appear()


def test_delete_vm_appear_after_refresh(setup_provider, provider):
    """ Tests delete vm

    Metadata:
        test_flag: delete_object
    """
    vm = provider.data['remove_test']['vm']
    test_vm = VM.factory(vm, provider)
    test_vm.delete()
    test_vm.wait_for_delete()
    provider.refresh_provider_relationships()
    test_vm.wait_to_appear()


def test_delete_template_appear_after_refresh(setup_provider, provider):
    """ Tests delete template

    Metadata:
        test_flag: delete_object
    """
    template = provider.data['remove_test']['template']
    test_template = VM.factory(template, provider, template=True)
    test_template.delete()
    test_template.wait_for_delete()
    provider.refresh_provider_relationships()
    test_template.wait_to_appear()


def test_delete_resource_pool_appear_after_refresh(setup_provider, provider):
    """ Tests delete pool

    Metadata:
        test_flag: delete_object
    """
    resourcepool_name = provider.data['remove_test']['resource_pool']
    test_resourcepool = resource_pool.ResourcePool(name=resourcepool_name)
    test_resourcepool.delete(cancel=False, wait=True)
    provider.refresh_provider_relationships()
    test_resourcepool.wait_for_exists()


@pytest.mark.meta(blockers=[1335961, 1467989])
@pytest.mark.ignore_stream("upstream")
def test_delete_datastore_appear_after_refresh(setup_provider, provider, appliance):
    """ Tests delete datastore

    Metadata:
        test_flag: delete_object
    """
    datastore_collection = appliance.collections.datastores
    data_store = provider.data['remove_test']['datastore']
    test_datastore = datastore_collection.instantiate(name=data_store, provider=provider)
    details_view = navigate_to(test_datastore, 'Details')

    host_count = int(details_view.entities.relationships.get_text_of('Hosts'))
    vm_count = int(details_view.entities.relationships.get_text_of('Managed VMs'))
    if host_count != "0":
        test_datastore.delete_all_attached_hosts()
    if vm_count != "0":
        test_datastore.delete_all_attached_vms()

    test_datastore.delete(cancel=False)
    wait_for(lambda: not test_datastore.exists, fail_condition=False,
             message="Wait datastore to disappear", num_sec=500,
             fail_func=test_datastore.browser.refresh)

    provider.refresh_provider_relationships()
    wait_for(lambda: test_datastore.exists, fail_condition=False,
             message="Wait datastore to appear", num_sec=1000,
             fail_func=test_datastore.browser.refresh)


def test_delete_cluster_from_table(setup_provider, provider, appliance):
    """ Tests delete cluster from table

    Metadata:
        test_flag: delete_object
    """
    cluster_name = provider.data['remove_test']['cluster']
    cluster_col = appliance.collections.clusters
    cluster1 = cluster_col.instantiate(name=cluster_name, provider=provider)
    cluster_col.delete(cluster1)
