"""Test to check v2v migration rest API"""
import fauxfactory
import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE


pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"]
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="second_provider",
        required_flags=["v2v"]
    )
]


@pytest.fixture(scope="function")
def get_clusters(appliance, v2v_providers):
    clusters = {}
    source_cluster = v2v_providers.vmware_provider.data.get("clusters")[0]
    target_cluster = v2v_providers.rhv_provider.data.get("clusters")[0]
    cluster_db = {
        cluster.name: cluster for cluster in appliance.rest_api.collections.clusters.all
    }

    if source_cluster in cluster_db.keys():
        clusters["source"] = cluster_db[source_cluster].href
    if target_cluster in cluster_db.keys():
        clusters["destination"] = cluster_db[target_cluster].href
    return clusters


@pytest.fixture(scope="function")
def get_datastores(appliance, v2v_providers):
    datastores = {}
    source_ds = [
        i.name for i in v2v_providers.vmware_provider.data.datastores if i.type == "nfs"][0]
    target_ds = [
        i.name for i in v2v_providers.rhv_provider.data.datastores if i.type == "nfs"][0]
    datastore_db = {
        ds.name: ds for ds in appliance.rest_api.collections.data_stores.all
    }

    if source_ds in datastore_db.keys():
        datastores["source"] = datastore_db[source_ds].href
    if target_ds in datastore_db.keys():
        datastores["destination"] = datastore_db[target_ds].href
    return datastores


@pytest.fixture(scope="function")
def get_networks(appliance, v2v_providers):
    networks = {}
    source_network = v2v_providers.vmware_provider.data.get("vlans", [None])[0]
    target_network = v2v_providers.rhv_provider.data.get("vlans", [None])[0]
    network_db = {
        network.name: network for network in appliance.rest_api.collections.lans.all
    }

    if source_network in network_db.keys():
        networks["source"] = network_db[source_network].href
    if target_network in network_db.keys():
        networks["destination"] = network_db[target_network].href
    return networks


def test_rest_mapping_create(request, appliance, get_clusters, get_datastores, get_networks):
    """Tests infrastructure mapping create"""
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
    """Tests infrastructure mapping bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.
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
