"""Test to check v2v migration rest API"""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import Templates
from cfme.fixtures.v2v_fixtures import get_vm
from cfme.fixtures.v2v_fixtures import set_conversion_host_api
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        required_flags=["v2v"],
        fixture_name="source_provider",
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.fixture(scope="function")
def get_clusters(appliance, provider, source_provider):
    clusters = {}
    try:
        source_cluster = source_provider.data.get("clusters")[0]
        target_cluster = provider.data.get("clusters")[0]
    except IndexError:
        pytest.skip("Cluster not found in given provider data")

    # Get the infra clusters object for vSphere and RHV prvoiders
    clusters_obj = appliance.rest_api.collections.clusters.all
    if provider.one_of(OpenStackProvider):
        clusters_obj += appliance.rest_api.collections.cloud_tenants.all

    cluster_db = {
        cluster.name: cluster for cluster in clusters_obj
    }

    try:
        if source_cluster in list(cluster_db.keys()):
            clusters["source"] = cluster_db[source_cluster].href
    except KeyError:
        pytest.skip("Cluster:{source_cluster} not found in {cluster_list}".format(
            source_cluster=source_cluster, cluster_list=list(cluster_db.keys())))

    try:
        if target_cluster in list(cluster_db.keys()):
            clusters["destination"] = cluster_db[target_cluster].href
    except KeyError:
        pytest.skip("Cluster:{target_cluster} not found in {cluster_list}".format(
            target_cluster=target_cluster, cluster_list=list(cluster_db.keys())))
    return clusters


@pytest.fixture(scope="function")
def get_datastores(appliance, provider, source_provider):
    datastores = {}
    # Get the infra datastores object for vSphere and RHV prvoiders
    datastores_obj = appliance.rest_api.collections.data_stores.all
    if provider.one_of(OpenStackProvider):
        target_type = "volume"
        datastores_obj += appliance.rest_api.collections.cloud_volume_types.all
    else:
        target_type = "nfs"

    try:
        source_ds = [
            i.name for i in source_provider.data.datastores if i.type == "nfs"][0]
        target_ds = [
            i.name for i in provider.data.datastores if i.type == target_type][0]
    except IndexError:
        pytest.skip("Datastore not found in given provider data")

    datastore_db = {
        ds.name: ds for ds in datastores_obj
    }

    try:
        if source_ds in list(datastore_db.keys()):
            datastores["source"] = datastore_db[source_ds].href
    except KeyError:
        pytest.skip("Datastore:{source_ds} not found in {ds_list}".format(
            source_ds=source_ds, ds_list=list(datastore_db.keys())))

    try:
        if target_ds in list(datastore_db.keys()):
            datastores["destination"] = datastore_db[target_ds].href
    except KeyError:
        pytest.skip("Datastore:{target_ds} not found in {ds_list}".format(
            target_ds=target_ds, ds_list=list(datastore_db.keys())))
    return datastores


@pytest.fixture(scope="function")
def get_networks(appliance, provider, source_provider):
    networks = {}
    # Get the network object for vSphere and RHV prvoiders
    networks_obj = appliance.rest_api.collections.lans.all

    try:
        source_network = source_provider.data.get("vlans", [None])[0]
        target_network = provider.data.get("vlans", [None])[0]
    except IndexError:
        pytest.skip("Network not found in given provider data")

    if provider.one_of(OpenStackProvider):
        networks_obj += appliance.rest_api.collections.cloud_networks.all

    network_db = {
        network.name: network for network in networks_obj
    }

    try:
        if source_network in list(network_db.keys()):
            networks["source"] = network_db[source_network].href
    except KeyError:
        pytest.skip("Network:{source_network} not found in {network_list}".format(
            source_network=source_network, network_list=list(network_db.keys())))

    try:
        if target_network in list(network_db.keys()):
            networks["destination"] = network_db[target_network].href
    except KeyError:
        pytest.skip("Network:{target_network} not found in {network_list}".format(
            target_network=target_network, network_list=list(network_db.keys())))
    return networks


def test_rest_mapping_create(request, appliance, get_clusters, get_datastores, get_networks):
    """
    Tests infrastructure mapping create

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.9
        tags: V2V
    """
    transformation_mappings = appliance.rest_api.collections.transformation_mappings.action.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        state="draft",
        transformation_mapping_items=[get_clusters, get_datastores, get_networks])[0]

    @request.addfinalizer
    def _cleanup():
        if transformation_mappings.exists:
            transformation_mappings.action.delete()

    assert transformation_mappings.exists


def test_rest_mapping_bulk_delete_from_collection(
        request, appliance, get_clusters, get_datastores, get_networks):
    """
    Tests infrastructure mapping bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.9
        tags: V2V
    """
    transformation_mappings = appliance.rest_api.collections.transformation_mappings
    data = [
        {
            "name": fauxfactory.gen_alphanumeric(),
            "description": fauxfactory.gen_alphanumeric(),
            "state": "draft",
            "transformation_mapping_items": [
                get_clusters,
                get_datastores,
                get_networks
            ]
        }
        for _ in range(2)
    ]
    mapping = transformation_mappings.action.create(*data)

    @request.addfinalizer
    def _cleanup():
        for m in mapping:
            if m.exists:
                m.action.delete()

    mapping[0].action.delete()
    transformation_mappings.action.delete(*mapping)
    assert appliance.rest_api.response
    results = appliance.rest_api.response.json()["results"]
    assert results[0]["success"] is False
    assert results[1]["success"] is True


@pytest.mark.parametrize("transformation_method", ["SSH", "VDDK67"])
def test_rest_conversion_host_crud(appliance, source_provider, provider, transformation_method):
    """
    Tests conversion host crud via REST
    Polarion:
        assignee: sshveta
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/2h
        startsin: 5.9
        tags: V2V
    """
    # Test1: Create two conversion host
    set_conversion_host_api(appliance, transformation_method, source_provider, provider)
    conversion_collection = appliance.rest_api.collections.conversion_hosts
    conv_host = conversion_collection.all

    # Test2: Edit first conversion host
    fixed_limit = 100
    edited_conv_host = conversion_collection.action.edit(
        id=conv_host[0].id,
        max_concurrent_tasks=fixed_limit)[0]
    assert edited_conv_host.max_concurrent_tasks == fixed_limit

    # Test3: Delete both conversion host
    for c in conv_host:
        response = conversion_collection.action.delete(id=c.id)[0]
        wait_for(
            lambda: response.state == "Finished",
            fail_func=response.reload,
            num_sec=240,
            delay=3,
            message="Waiting for conversion host configuration task to be deleted")
    assert not conversion_collection.all


@pytest.mark.provider([RHEVMProvider], selector=ONE_PER_VERSION,
                      required_flags=["v2v"], scope='module')
@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [
        ["nfs", "iscsi", Templates.RHEL7_MINIMAL]
    ]
)
def test_rest_plan_create(request, appliance, get_clusters, get_datastores, get_networks,
                          source_type, dest_type, template_type, source_provider
                          ):
    """
    Tests migration plan create via API

    Polarion:
        assignee: sshveta
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.9
        tags: V2V
    """
    transformation_mappings = appliance.rest_api.collections.transformation_mappings.action.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        state="draft",
        transformation_mapping_items=[get_clusters, get_datastores, get_networks])[0]

    vm_obj = get_vm(request, appliance, source_provider, Templates.RHEL7_MINIMAL)
    vm = appliance.rest_api.collections.vms.get(name=vm_obj.name)

    migration_plan = appliance.rest_api.collections.service_templates.action.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        prov_type="generic_transformation_plan",
        config_info={"transformation_mapping_id": transformation_mappings.id,
                     "pre_service_id": "",
                     "post_service_id": "",
                     "actions": [{"vm_id": vm.id,
                                  "post_service": "false",
                                  "pre_service": "false",
                                  }]})[0]

    @request.addfinalizer
    def _cleanup():
        if migration_plan.exists:
            migration_plan.action.delete()

    assert migration_plan.exists
