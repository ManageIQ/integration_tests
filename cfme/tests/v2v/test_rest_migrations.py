"""Test to check v2v migration rest API"""
import fauxfactory
import pytest

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION


pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"]
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="second_provider",
        required_flags=["v2v"]
    )
]


@pytest.fixture(scope="function")
def get_clusters(appliance, v2v_providers):
    clusters = {}
    source_cluster = v2v_providers.vmware_provider.data.get("clusters")[0]
    target_cluster = v2v_providers.rhv_provider.data.get("clusters")[0]
    cluster = appliance.rest_api.collections.clusters.all
    for cl in cluster:
        if cl.name == source_cluster:
            clusters["source"] = "/api/clusters/{}".format(cl.id)
        elif cl.name == target_cluster:
            clusters["destination"] = "/api/clusters/{}".format(cl.id)
    return clusters


@pytest.fixture(scope="function")
def get_datastores(appliance, v2v_providers):
    datastores = {}
    datastore = appliance.rest_api.collections.data_stores.all
    source_ds = [
        i.name for i in v2v_providers.vmware_provider.data.datastores if i.type == "nfs"][0]
    target_ds = [
        i.name for i in v2v_providers.rhv_provider.data.datastores if i.type == "nfs"][0]
    for ds in datastore:
        if ds.name == source_ds:
            datastores["source"] = "/api/data_stores/{}".format(ds.id)
        elif ds.name == target_ds:
            datastores["destination"] = "/api/data_stores/{}".format(ds.id)
    return datastores


@pytest.fixture(scope="function")
def get_networks(appliance, v2v_providers):
    networks = {}
    source_network = v2v_providers.vmware_provider.data.get("vlans", [None])[0]
    target_network = v2v_providers.rhv_provider.data.get("vlans", [None])[0]
    network = appliance.rest_api.collections.lans.all
    for n in network:
        if n.name == source_network:
            networks["source"] = "/api/lans/{}".format(n.id)
        elif n.name == target_network:
            networks["destination"] = "/api/lans/{}".format(n.id)
    return networks


def test_rest_mapping_create(request, appliance, get_clusters, get_datastores, get_networks):
    """Tests infrastructure mapping create"""
    collection = appliance.rest_api.collections.transformation_mappings.action.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        state="draft",
        transformation_mapping_items=[get_clusters, get_datastores, get_networks])[0]

    @request.addfinalizer
    def _cleanup():
        if collection.exists:
            collection.action.delete()

    assert appliance.rest_api.response


def test_rest_mapping_bulk_delete_from_collection(
        request, appliance, get_clusters, get_datastores, get_networks):
    """Tests infrastructure mapping bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.
    """
    collection = appliance.rest_api.collections.transformation_mappings
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
    mapping = collection.action.create(*data)

    @request.addfinalizer
    def _cleanup():
        for m in mapping:
            if m.exists:
                m.action.delete()

    mapping[0].action.delete()
    collection.action.delete(*mapping)
    assert appliance.rest_api.response
    results = appliance.rest_api.response.json()["results"]
    assert results[0]["success"] is False
    assert results[1]["success"] is True
