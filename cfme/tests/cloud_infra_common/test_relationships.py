# -*- coding: utf-8 -*-
import random

import pytest

from cfme.cloud.availability_zone import ProviderAvailabilityZoneAllView, AvailabilityZone
from cfme.cloud.flavor import ProviderFlavorAllView, Flavor
from cfme.cloud.instance import Instance
from cfme.cloud.instance.image import Image
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider import CloudProviderImagesView, CloudProviderInstancesView
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.stack import ProviderStackAllView
from cfme.cloud.tenant import ProviderTenantAllView
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider import CloudInfraProvider
from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.vm_views import HostAllVMsView, ProviderAllVMsView
from cfme.infrastructure.cluster import ClusterDetailsView, ProviderAllClustersView
from cfme.infrastructure.datastore import HostAllDatastoresView, ProviderAllDatastoresView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import (HostTemplatesOnlyAllView,
                                                  ProviderTemplatesOnlyAllView, InfraVm, Template)
from cfme.markers.env_markers.provider import ONE, ONE_PER_TYPE
from cfme.networks.provider import NetworkProvider
from cfme.networks.views import NetworkProviderDetailsView, ProviderSecurityGroupAllView
from cfme.storage.manager import ProviderStorageManagerAllView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

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
    ("Cloud tenants", ProviderTenantAllView),
    ("Flavors", ProviderFlavorAllView),
    ("Security Groups", ProviderSecurityGroupAllView),
    ("Instances", CloudProviderInstancesView),
    ("Images", CloudProviderImagesView),
    ("Orchestration stacks", ProviderStackAllView),
    ("Storage Managers", ProviderStorageManagerAllView)
]
# TODO: add Host Aggregates view to CLOUD_PROVIDER_RELATIONSHIPS

cloud_test_items = [
    ("instances", Instance),
    ("flavors", Flavor),
    ("availability_zones", AvailabilityZone),
    ("cloud_tenants", None),
    ("images", Image),
    ("security_groups", None),
    ("stacks", None),
    ("block_managers", None),
    ("network_providers", None)
]

infra_test_items = [
    ("clusters", None),
    ("hosts", None),
    ("datastores", None),
    ("vms", InfraVm),
    ("templates", Template)
]


def _fix_item(appliance, item):
    # Some version-dependent things ...
    if item == 'Orchestration stacks' and appliance.version >= '5.9':
        return 'Orchestration Stacks'
    elif item == 'Availability zones' and appliance.version >= '5.9':
        return 'Availability Zones'
    elif item == 'Cloud tenants' and appliance.version >= '5.9':
        return 'Cloud Tenants'
    else:
        return item


RELATIONSHIPS = {
    "Infrastructure Provider", "Availability zones", "Availability Zones", "Flavors",
    "Security Groups", "Instances", "Images", "Orchestration stacks", "Orchestration Stacks",
    "Storage Managers", "Cloud Tenants", "Cloud tenants"}


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
        obj = network_providers_col.instantiate(prov_class=NetworkProvider, name=network_prov_name)
    return obj


@pytest.fixture
def host(appliance, provider):
    host_collection = appliance.collections.hosts
    expression = 'fill_field(Host / Node : Parent Cluster, IS NOT NULL)'
    view = navigate_to(host_collection, 'All')
    view.entities.search.advanced_search(expression)
    return random.choice(host_collection.all(provider))


def wait_for_relationship_refresh(provider):
    view = navigate_to(provider, 'Details')
    logger.info('Waiting for relationship refresh')
    wait_for(
        lambda: (view.entities.summary("Status").get_text_of('Last Refresh') ==
                 'Success - Less Than A Minute Ago'),
        delay=15,
        timeout=110,
        fail_func=view.browser.refresh)


@pytest.mark.rhv3
@pytest.mark.parametrize("relationship,view", HOST_RELATIONSHIPS,
    ids=[rel[0] for rel in HOST_RELATIONSHIPS])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE)
def test_host_relationships(appliance, provider, setup_provider, host, relationship, view):
    """Tests relationship navigation for a host

    Polarion:
        assignee: ansinha
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    host_view = navigate_to(host, "Details")
    if host_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    obj = get_obj(relationship, appliance, provider=provider, host=host)
    host_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed


@pytest.mark.rhv3
@pytest.mark.parametrize("relationship,view", INFRA_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in INFRA_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE)
def test_infra_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for an infrastructure provider

    Polarion:
        assignee: ansinha
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    provider_view = navigate_to(provider, "Details")
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': provider})
    assert relationship_view.is_displayed


@pytest.mark.parametrize("relationship,view", CLOUD_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in CLOUD_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([CloudProvider], selector=ONE_PER_TYPE)
def test_cloud_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for a cloud provider

    Polarion:
        assignee: ansinha
        casecomponent: cloud
        caseimportance: medium
        initialEstimate: 1/12h
    """
    # Version dependent strings
    relationship = _fix_item(appliance, relationship)
    provider_view = navigate_to(provider, "Details")
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip("There are no relationships for {}".format(relationship))
    obj = get_obj(relationship, appliance, provider=provider)
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed


@pytest.fixture(scope='function')
def prov_child_visibility(appliance, provider, request, tag, user_restricted):
    def _prov_child_visibility(relationship, item_cls, visibility):
        provider.add_tag(tag=tag)
        if not item_cls:
            item_cls = getattr(appliance.collections, relationship)
        actual_visibility = _check_actual_visibility(item_cls)
        if not actual_visibility:
            pytest.skip("There are no relationships for {}".format(relationship))

        @request.addfinalizer
        def _finalize():
            provider.remove_tag(tag=tag)

        with user_restricted:
            actual_visibility = _check_actual_visibility(item_cls)

        assert actual_visibility == visibility

    def _check_actual_visibility(item_cls):
        view = navigate_to(item_cls, 'All')
        try:
            if hasattr(view.entities, 'entity_names'):
                assert view.entities.entity_names
            else:
                # this case is specified for block_managers
                if appliance.version >= '5.9':
                    assert view.entities.read()
                else:
                    assert view.entities.read().get('table')
            actual_visibility = True
        except AssertionError:
            actual_visibility = False
        return actual_visibility

    return _prov_child_visibility


@pytest.mark.parametrize("relationship,item_cls", infra_test_items,
    ids=[rel[0] for rel in infra_test_items])
@pytest.mark.provider([VMwareProvider], selector=ONE)
# used VMwareProvider to cover all relationship as they have each of them
def test_tagvis_infra_provider_children(prov_child_visibility, setup_provider, relationship,
                                        item_cls):
    """ Tests that provider child's should not be visible for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to provider
        2. Login as restricted user, providers child not visible for user

    Polarion:
        assignee: rbabyuk
        initialEstimate: None
    """
    prov_child_visibility(relationship, item_cls, visibility=False)


@pytest.mark.parametrize("relationship,item_cls", cloud_test_items,
    ids=[rel[0] for rel in cloud_test_items])
@pytest.mark.provider([OpenStackProvider], selector=ONE)
# used OpenStackProvider to cover all relationship as they have each of them
@pytest.mark.tier(2)
def test_tagvis_cloud_provider_children(prov_child_visibility, setup_provider, relationship,
                                        item_cls):
    """ Tests that provider child's should not be visible for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to provider
        2. Login as restricted user, providers child not visible for user

    Polarion:
        assignee: rbabyuk
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/8h
    """
    prov_child_visibility(relationship, item_cls, visibility=False)


@pytest.mark.rhv1
@pytest.mark.provider([CloudInfraProvider])
def test_provider_refresh_relationship(provider, setup_provider):
    """
    Polarion:
        assignee: ansinha
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/12h
    """
    provider.refresh_provider_relationships(method='ui')
    wait_for_relationship_refresh(provider)
