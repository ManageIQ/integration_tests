# -*- coding: utf-8 -*-
import pytest
import random

from cfme.cloud.availability_zone import ProviderAvailabilityZoneAllView
from cfme.cloud.flavor import ProviderFlavorAllView
from cfme.cloud.provider import CloudProviderImagesView, CloudProviderInstancesView
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.stack import ProviderStackAllView
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.vm_views import HostAllVMsView, ProviderAllVMsView
from cfme.infrastructure.cluster import ClusterDetailsView, ProviderAllClustersView
from cfme.infrastructure.datastore import HostAllDatastoresView, ProviderAllDatastoresView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import (HostTemplatesOnlyAllView,
    ProviderTemplatesOnlyAllView)
from cfme.networks.views import NetworkProviderDetailsView, ProviderSecurityGroupAllView
from cfme.storage.manager import ProviderStorageManagerAllView
from cfme.utils.appliance.implementations.ui import navigate_to
from markers.env_markers.provider import ONE_PER_TYPE


HOST_RELATIONSHIPS = [
    ("Infrastructure Provider", InfraProviderDetailsView),
    ("Cluster", ClusterDetailsView),
    ("Datastores", HostAllDatastoresView),
    ("VMs", HostAllVMsView),
    ("Templates", HostTemplatesOnlyAllView)
]


INFRA_PROVIDER_RELATIONSHIPS = [
    ("Clusters", ProviderAllClustersView),
    ("Hosts", ProviderAllHostsView),
    ("Datastores", ProviderAllDatastoresView),
    ("Virtual Machines", ProviderAllVMsView),
    ("Templates", ProviderTemplatesOnlyAllView)

]


CLOUD_PROVIDER_RELATIONSHIPS = [
    ("Network Manager", NetworkProviderDetailsView),
    ("Availability zones", ProviderAvailabilityZoneAllView),
    ("Flavors", ProviderFlavorAllView),
    ("Security Groups", ProviderSecurityGroupAllView),
    ("Instances", CloudProviderInstancesView),
    ("Images", CloudProviderImagesView),
    ("Orchestration stacks", ProviderStackAllView),
    ("Storage Managers", ProviderStorageManagerAllView)
]


def _fix_item(appliance, item):
    # Some version-dependent things ...
    if item == 'Orchestration stacks' and appliance.version >= '5.9':
        return 'Orchestration Stacks'
    elif item == 'Availability zones' and appliance.version >= '5.9':
        return 'Availability Zones'
    else:
        return item


RELATIONSHIPS = {
    "Infrastructure Provider", "Availability zones", "Availability Zones", "Flavors",
    "Security Groups", "Instances", "Images", "Orchestration stacks", "Orchestration Stacks",
    "Storage Managers"}


def get_obj(relationship, appliance, **kwargs):
    if relationship in RELATIONSHIPS:
        obj = kwargs.get("provider")
    elif relationship == "Cluster":
        cluster_col = appliance.collections.clusters
        host = kwargs.get("host")
        provider = kwargs.get("provider")
        view = navigate_to(host, "Details")
        cluster_name = view.entities.summary("Relationships").get_text_of("Cluster")
        obj = cluster_col.instantiate(name=cluster_name, provider=provider)
    elif relationship in ["Datastores", "VMs", "Templates"]:
        obj = kwargs.get("host")
    elif relationship == "Network Manager":
        network_providers_col = appliance.collections.network_providers
        provider = kwargs.get("provider")
        view = navigate_to(provider, "Details")
        network_prov_name = view.entities.summary("Relationships").get_text_of("Network Manager")
        obj = network_providers_col.instantiate(name=network_prov_name)
    return obj


@pytest.fixture
def host(appliance, provider):
    host_collection = appliance.collections.hosts
    return random.choice(host_collection.all(provider))


@pytest.mark.parametrize("relationship,view", HOST_RELATIONSHIPS,
    ids=[rel[0] for rel in HOST_RELATIONSHIPS])
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
def test_host_relationships(appliance, provider, setup_provider, host, relationship, view):
    """Tests relationship navigation for a host"""
    host_view = navigate_to(host, "Details")
    if host_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    obj = get_obj(relationship, appliance, provider=provider, host=host)
    host_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed


@pytest.mark.parametrize("relationship,view", INFRA_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in INFRA_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
def test_infra_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for an infrastructure provider"""
    provider_view = navigate_to(provider, "Details")
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': provider})
    assert relationship_view.is_displayed


@pytest.mark.parametrize("relationship,view", CLOUD_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in CLOUD_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([EC2Provider], selector=ONE_PER_TYPE)
def test_cloud_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for a cloud provider"""
    # Version dependent strings
    relationship = _fix_item(appliance, relationship)
    provider_view = navigate_to(provider, "Details")
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    obj = get_obj(relationship, appliance, provider=provider)
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed
