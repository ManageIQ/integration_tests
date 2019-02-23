"""Test to check v2v migration rest API"""
import fauxfactory
import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION


pytestmark = [
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=['v2v'],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name='source_provider',
        required_flags=['v2v'],
        scope="module"
    )
]


@pytest.fixture(scope="function")
def get_clusters(appliance, v2v_providers):
    clusters = {}
    try:
        source_cluster = v2v_providers.vmware_provider.data.get("clusters")[0]
        target_cluster = v2v_providers.rhv_provider.data.get("clusters")[0]
    except IndexError:
        pytest.skip("Cluster not found in given provider data")
    cluster_db = {
        cluster.name: cluster for cluster in appliance.rest_api.collections.clusters.all
    }

    try:
        if source_cluster in cluster_db.keys():
            clusters["source"] = cluster_db[source_cluster].href
    except KeyError:
        pytest.skip("Cluster:{source_cluster} not found in {cluster_list}".format(
            source_cluster=source_cluster, cluster_list=cluster_db.keys()))

    try:
        if target_cluster in cluster_db.keys():
            clusters["destination"] = cluster_db[target_cluster].href
    except KeyError:
        pytest.skip("Cluster:{target_cluster} not found in {cluster_list}".format(
            target_cluster=target_cluster, cluster_list=cluster_db.keys()))
    return clusters


@pytest.fixture(scope="function")
def get_datastores(appliance, v2v_providers):
    datastores = {}
    try:
        source_ds = [
            i.name for i in v2v_providers.vmware_provider.data.datastores if i.type == "nfs"][0]
        target_ds = [
            i.name for i in v2v_providers.rhv_provider.data.datastores if i.type == "nfs"][0]
    except IndexError:
        pytest.skip("Datastore not found in given provider data")
    datastore_db = {
        ds.name: ds for ds in appliance.rest_api.collections.data_stores.all
    }

    try:
        if source_ds in datastore_db.keys():
            datastores["source"] = datastore_db[source_ds].href
    except KeyError:
        pytest.skip("Datastore:{source_ds} not found in {ds_list}".format(
            source_ds=source_ds, ds_list=datastore_db.keys()))

    try:
        if target_ds in datastore_db.keys():
            datastores["destination"] = datastore_db[target_ds].href
    except KeyError:
        pytest.skip("Datastore:{target_ds} not found in {ds_list}".format(
            target_ds=target_ds, ds_list=datastore_db.keys()))
    return datastores


@pytest.fixture(scope="function")
def get_networks(appliance, v2v_providers):
    networks = {}
    try:
        source_network = v2v_providers.vmware_provider.data.get("vlans", [None])[0]
        target_network = v2v_providers.rhv_provider.data.get("vlans", [None])[0]
    except IndexError:
        pytest.skip("Network not found in given provider data")
    network_db = {
        network.name: network for network in appliance.rest_api.collections.lans.all
    }

    try:
        if source_network in network_db.keys():
            networks["source"] = network_db[source_network].href
    except KeyError:
        pytest.skip("Network:{source_network} not found in {network_list}".format(
            source_network=source_network, network_list=network_db.keys()))

    try:
        if target_network in network_db.keys():
            networks["destination"] = network_db[target_network].href
    except KeyError:
        pytest.skip("Network:{target_network} not found in {network_list}".format(
            target_network=target_network, network_list=network_db.keys()))
    return networks


def test_rest_mapping_create(request, appliance, get_clusters, get_datastores, get_networks):
    """
    Tests infrastructure mapping create

    Polarion:
        assignee: ytale
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        subcomponent: RHV
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
        assignee: ytale
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        subcomponent: RHV
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


def test_rest_conversion_create(request, appliance):
    """
    Tests conversion host create

    Polarion:
        assignee: ytale
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        subcomponent: RHV
        startsin: 5.9
        tags: V2V
    """
    conversion_host = appliance.rest_api.collections.conversion_hosts.action.create(
        name=fauxfactory.gen_alphanumeric(),
        resource_type="Host",
        resource_id=1,
        vddk_transport_supported="true",
        ssh_transport_supported="false")[0]

    @request.addfinalizer
    def _cleanup():
        if conversion_host.exists:
            conversion_host.action.delete()

    assert conversion_host.exists


def test_rest_conversion_bulk_delete_from_collection(request, appliance):
    """
    Tests conversion host bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.

    Polarion:
        assignee: ytale
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/8h
        subcomponent: RHV
        startsin: 5.9
        tags: V2V
    """
    conversion_host = appliance.rest_api.collections.conversion_hosts
    data = [
        {
            "name": fauxfactory.gen_alphanumeric(),
            "resource_type": "Host",
            "resource_id": 1,
            "vddk_transport_supported": "true",
            "ssh_transport_supported": "false"
        }
        for _ in range(2)
    ]
    hosts_obj = conversion_host.action.create(*data)

    @request.addfinalizer
    def _cleanup():
        for m in hosts_obj:
            if m.exists:
                m.action.delete()  # delete by post method

    hosts_obj[0].action.delete()
    conversion_host.action.delete(*hosts_obj)  # delete by delete method
    assert appliance.rest_api.response
    results = appliance.rest_api.response.json()["results"]
    assert results[0]["success"] is False
    assert results[1]["success"] is True
