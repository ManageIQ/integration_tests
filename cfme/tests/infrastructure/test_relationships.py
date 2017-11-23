# -*- coding: utf-8 -*-
import pytest
import random

from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.vm_views import HostAllVMsView
from cfme.infrastructure.cluster import ClusterDetailsView
from cfme.infrastructure.datastore import HostAllDatastoresView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from markers.env_markers.provider import ONE_PER_TYPE


RELATIONSHIPS = [
    ("Infrastructure Provider", InfraProviderDetailsView, "providers"),
    ("Cluster", ClusterDetailsView, "clusters"),
    ("Datastores", HostAllDatastoresView, "datastores"),
    ("VMs", HostAllVMsView, "vms")
]


def get_obj(host, collection, appliance, provider):
    if collection == "providers":
        obj = provider
    elif collection == "clusters":
        cluster_col = appliance.collections.clusters
        cluster_name = host.get_detail("Relationships", "Cluster")
        obj = cluster_col.instantiate(name=cluster_name, provider=provider)
    elif collection == "datastores":
        obj = host
    elif collection == "vms":
        obj = host
    return obj


@pytest.fixture(scope="module")
def host(appliance, provider):
    host_collection = appliance.collections.hosts
    return random.choice(host_collection.all(provider))


@pytest.mark.parametrize("relationship,view,collection", RELATIONSHIPS,
    ids=[rel[2] for rel in RELATIONSHIPS])
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
def test_host_relationships(appliance, host, setup_provider, provider, relationship, view,
        collection):
    """Tests relationship navigation for a host"""
    host_view = navigate_to(host, "Details")
    obj = get_obj(host, collection, appliance, provider)
    host_view.entities.relationships.click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed
