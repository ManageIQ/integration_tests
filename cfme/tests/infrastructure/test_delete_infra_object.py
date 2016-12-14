# -*- coding: utf-8 -*-

import pytest
from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure import host, datastore, cluster, resource_pool
from cfme.infrastructure.provider import InfraProvider
from cfme.web_ui import Region
from utils import testgen

pytestmark = [pytest.mark.tier(3),
              test_requirements.general_ui]

details_page = Region(infoblock_type='detail')


pytest_generate_tests = testgen.generate(
    [InfraProvider], required_fields=['remove_test'], scope="module")


def test_delete_cluster(setup_provider, provider):
    """ Tests delete cluster

    Metadata:
        test_flag: delete_object
    """
    cluster_name = provider.data['remove_test']['cluster']
    test_cluster = cluster.Cluster(name=cluster_name, provider=provider)
    test_cluster.delete(cancel=False)
    test_cluster.wait_for_delete()
    provider.refresh_provider_relationships()
    test_cluster.wait_for_appear()


def test_delete_host(setup_provider, provider):
    """ Tests delete host

    Metadata:
        test_flag: delete_object
    """
    host_name = provider.data['remove_test']['host']
    test_host = host.Host(name=host_name)
    test_host.delete(cancel=False)
    host.wait_for_host_delete(test_host)
    provider.refresh_provider_relationships()
    host.wait_for_host_to_appear(test_host)


def test_delete_vm(setup_provider, provider):
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


def test_delete_template(setup_provider, provider):
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


def test_delete_resource_pool(setup_provider, provider):
    """ Tests delete pool

    Metadata:
        test_flag: delete_object
    """
    resourcepool_name = provider.data['remove_test']['resource_pool']
    test_resourcepool = resource_pool.ResourcePool(name=resourcepool_name)
    test_resourcepool.delete(cancel=False)
    test_resourcepool.wait_for_delete()
    provider.refresh_provider_relationships()
    test_resourcepool.wait_for_appear()


@pytest.mark.meta(blockers=[1236977, 1335961])
@pytest.mark.ignore_stream("upstream")
def test_delete_datastore(setup_provider, provider):
    """ Tests delete datastore

    Metadata:
        test_flag: delete_object
    """
    data_store = provider.data['remove_test']['datastore']
    test_datastore = datastore.Datastore(name=data_store)
    host_count = test_datastore.get_detail('Relationships', 'Hosts')
    vm_count = test_datastore.get_detail('Relationships', 'Managed VMs')
    if host_count != "0":
        test_datastore.delete_all_attached_hosts()
        test_datastore.wait_for_delete_all()
    if vm_count != "0":
        test_datastore.delete_all_attached_vms()
        test_datastore.wait_for_delete_all()
    test_datastore.delete(cancel=False)
    test_datastore.wait_for_delete()
    provider.refresh_provider_relationships()
    test_datastore.wait_for_appear()
