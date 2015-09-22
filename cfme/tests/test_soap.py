#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from random import choice

from utils import testgen
from utils.blockers import BZ
from utils.miq_soap import MiqVM, set_client
from utils.providers import setup_a_provider as _setup_a_provider

pytest_generate_tests = testgen.generate(
    testgen.infra_providers,
    "small_template",
    scope="class"
)

pytestmark = [pytest.mark.ignore_stream("5.5", "upstream")]


@pytest.fixture(scope="class")
def setup_a_provider():
    _setup_a_provider("infra")


@pytest.mark.usefixtures("setup_a_provider")
class TestSoapBasicInteraction(object):
    def test_connectivity(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert soap_client.service.EVMPing(), "Could not do EVMPing()!"

    def test_evm_host_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.EVMHostList(), list)

    def test_evm_vm_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.EVMVmList("*"), list)

    def test_evm_cluster_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.EVMClusterList(), list)

    def test_evm_resource_pool_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.EVMResourcePoolList(), list)

    def test_evm_datastore_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.EVMDatastoreList(), list)

    def test_get_ems_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.GetEmsList(), list)

    def test_version(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        assert isinstance(soap_client.service.Version(), list)

    @pytest.mark.meta(blockers=[1096768])
    def test_get_hosts_from_ems(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for ems in soap_client.service.GetEmsList():
            assert isinstance(soap_client.service.EVMGetHosts(ems.guid), list)

    def test_get_host(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for host in soap_client.service.EVMHostList():
            get_host = soap_client.service.EVMGetHost(host.guid)
            assert get_host.guid == host.guid
            assert get_host.name == host.name

    @pytest.mark.meta(blockers=[1096768])
    def test_get_clusters_from_ems(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for ems in soap_client.service.GetEmsList():
            assert isinstance(soap_client.service.EVMGetClusters(ems.guid), list)

    @pytest.mark.meta(blockers=[1096708])
    def test_get_cluster(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for cluster in soap_client.service.EVMClusterList():
            get_cluster = soap_client.service.EVMGetCluster(cluster.id)
            assert get_cluster.id == cluster.id
            assert get_cluster.name == cluster.name

    @pytest.mark.meta(blockers=[1096768])
    def test_get_resource_pools_from_ems(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for ems in soap_client.service.GetEmsList():
            assert isinstance(soap_client.service.EVMGetResourcePools(ems.guid), list)

    @pytest.mark.meta(blockers=[1096708])
    def test_get_resource_pool(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for resource_pool in soap_client.service.EVMResourcePoolList():
            get_resource_pool = soap_client.service.EVMGetResourcePool(resource_pool.id)
            assert get_resource_pool.id == resource_pool.id
            assert get_resource_pool.name == resource_pool.name

    @pytest.mark.meta(blockers=[1096768])
    def test_get_datastores_from_ems(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for ems in soap_client.service.GetEmsList():
            assert isinstance(soap_client.service.EVMGetDatastores(ems.guid), list)

    @pytest.mark.meta(blockers=[1096708])
    def test_get_datastore(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        for datastore in soap_client.service.EVMDatastoreList():
            get_datastore = soap_client.service.EVMGetDatastore(datastore.id)
            assert get_datastore.id == datastore.id
            assert get_datastore.name == datastore.name

    @pytest.mark.meta(blockers=[1096768])
    def test_get_vms_from_host(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        host = choice(soap_client.service.EVMHostList())
        vms = soap_client.service.EVMGetVms(host.guid)
        assert isinstance(vms, list)
        for vm in vms:
            get_vm = soap_client.service.EVMGetVm(vm.guid)
            assert get_vm.guid == vm.guid
            assert get_vm.name == vm.name

    def test_get_host_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        assert isinstance(soap_client.service.GetHostList(ems.guid), list)

    def test_get_cluster_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        assert isinstance(soap_client.service.GetClusterList(ems.guid), list)

    def test_get_resource_pool_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        assert isinstance(soap_client.service.GetResourcePoolList(ems.guid), list)

    def test_get_datastore_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        assert isinstance(soap_client.service.GetDatastoreList(ems.guid), list)

    def test_get_vm_list(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        host = choice(soap_client.service.EVMHostList())
        assert isinstance(soap_client.service.GetVmList(host.guid), list)

    def test_find_ems_by_guid(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        get_ems = soap_client.service.FindEmsByGuid(ems.guid)
        assert get_ems.guid == ems.guid
        assert get_ems.name == ems.name

    def test_find_host_by_guid(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        host = choice(soap_client.service.EVMHostList())
        get_host = soap_client.service.FindHostByGuid(host.guid)
        assert get_host.guid == host.guid
        assert get_host.name == host.name
        assert isinstance(soap_client.service.FindHostsByGuid(host.guid), list)

    def test_find_cluster_by_id(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        cluster = choice(soap_client.service.EVMClusterList())
        get_cluster = soap_client.service.FindClusterById(cluster.id)
        assert get_cluster.id == cluster.id
        assert get_cluster.name == cluster.name
        assert isinstance(soap_client.service.FindClustersById(cluster.id), list)

    def test_find_datastore_by_id(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        datastore = choice(soap_client.service.EVMDatastoreList())
        get_datastore = soap_client.service.FindDatastoreById(datastore.id)
        assert get_datastore.id == datastore.id
        assert get_datastore.name == datastore.name
        assert isinstance(soap_client.service.FindDatastoresById(datastore.id), list)

    def test_find_resource_pool_by_id(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        resource_pool = choice(soap_client.service.EVMResourcePoolList())
        get_resource_pool = soap_client.service.FindResourcePoolById(resource_pool.id)
        assert get_resource_pool.id == resource_pool.id
        assert get_resource_pool.name == resource_pool.name
        assert isinstance(soap_client.service.FindResourcePoolsById(resource_pool.id), list)

    # Goes through hosts because EVMVmList does not work at all.
    def test_find_vm_by_guid(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        vm = choice(soap_client.service.EVMVmList("*"))
        get_vm = soap_client.service.FindVmByGuid(vm.guid)
        assert get_vm.guid == vm.guid
        assert get_vm.name == vm.name
        assert isinstance(soap_client.service.FindVmsByGuid(vm.guid), list)

    # Goes through hosts because EVMVmList does not work at all.
    def test_evm_vm_software(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        vm = choice(soap_client.service.EVMVmList("*"))
        assert isinstance(soap_client.service.EVMVmSoftware(vm.guid), list)

    # Goes through hosts because EVMVmList does not work at all.
    def test_evm_vm_accounts(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        vm = choice(soap_client.service.EVMVmList("*"))
        assert isinstance(soap_client.service.EVMVmAccounts(vm.guid), list)

    def test_ems_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        ems = choice(soap_client.service.GetEmsList())
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.EmsGetTags(ems.guid):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.EmsSetTag(ems.guid, "cc", cc)
        for tag in soap_client.service.EmsGetTags(ems.guid):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for Ems {}".format(ems.name))

    def test_cluster_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        cluster = choice(soap_client.service.EVMClusterList())
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.ClusterGetTags(cluster.id):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.ClusterSetTag(cluster.id, "cc", cc)
        for tag in soap_client.service.ClusterGetTags(cluster.id):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for cluster {}".format(cluster.name))

    def test_datastore_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        datastore = choice(soap_client.service.EVMDatastoreList())
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.DatastoreGetTags(datastore.id):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.DatastoreSetTag(datastore.id, "cc", cc)
        for tag in soap_client.service.DatastoreGetTags(datastore.id):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for datastore {}".format(datastore.name))

    def test_host_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        host = choice(soap_client.service.EVMHostList())
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.HostGetTags(host.guid):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.HostSetTag(host.guid, "cc", cc)
        for tag in soap_client.service.HostGetTags(host.guid):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for host {}".format(host.name))

    def test_resource_pool_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        pool = choice(soap_client.service.EVMResourcePoolList())
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.ResourcePoolGetTags(pool.id):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.ResourcePoolSetTag(pool.id, "cc", cc)
        for tag in soap_client.service.ResourcePoolGetTags(pool.id):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for pool {}".format(pool.name))

    def test_vm_tagging(self, soap_client):
        """Tests soap

        Metadata:
            test_flag: soap
        """
        vm = choice(soap_client.service.EVMVmList("*"))
        # Prepare (find the opposite tag if already tagged)
        cc = "001"
        for tag in soap_client.service.VmGetTags(vm.guid):
            if tag.category == "cc":
                if tag.tag_name == cc:
                    cc = "002"
                break
        # Tag!
        soap_client.service.VmSetTag(vm.guid, "cc", cc)
        for tag in soap_client.service.VmGetTags(vm.guid):
            if tag.category == "cc" and tag.tag_name == cc:
                break
        else:
            pytest.fail("Could not find tags for vm {}".format(vm.name))


class TestProvisioning(object):
    WAIT_TIME = 300
    WAIT_TIME_SLOW = 600
    SLOW_PROVIDERS = {"rhevm", "scvmm"}

    @pytest.mark.meta(
        server_roles="+automate",
        blockers=[
            BZ(1118831, unblock=lambda appliance_version: appliance_version < "5.3"),
            1131480,
            1132578
        ]
    )
    @pytest.mark.usefixtures("setup_provider_clsscope")
    def test_provision_via_soap(self, request, soap_client, provider, small_template):
        """Tests soap

        Metadata:
            test_flag: soap, provision
        """
        # rhev-m and scvmm need extra time to make their minds
        wtime = self.WAIT_TIME if provider.type not in self.SLOW_PROVIDERS else self.WAIT_TIME_SLOW
        vm_name = "test_soap_provision_{}".format(fauxfactory.gen_alphanumeric())
        vlan = provider.data.get("provisioning", {}).get("vlan", None)

        def _cleanup():
            try:
                if provider.mgmt.does_vm_exist(vm_name):
                    provider.mgmt.delete_vm(vm_name)
            except:
                pass

        request.addfinalizer(_cleanup)
        set_client(soap_client)
        vm = MiqVM.provision_from_template(small_template, vm_name, vlan=vlan, wait_min=10,)
        request.addfinalizer(lambda: vm.delete() if vm.exists else None)
        if vm.is_powered_on:
            vm.power_off()
            vm.wait_powered_off(wait_time=wtime)
        vm.power_on()
        vm.wait_powered_on(wait_time=wtime)
