import random

import pytest
from navmazing import NavigationDestinationNotFound

from cfme import test_requirements
from cfme.cloud.availability_zone import ProviderAvailabilityZoneAllView
from cfme.cloud.flavor import ProviderFlavorAllView
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider import CloudProviderImagesView
from cfme.cloud.provider import CloudProviderInstancesView
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.stack import ProviderStackAllView
from cfme.cloud.tenant import ProviderTenantAllView
from cfme.common.datastore_views import HostAllDatastoresView
from cfme.common.datastore_views import ProviderAllDatastoresView
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider_views import InfraProviderDetailsView
from cfme.common.vm_views import HostAllVMsView
from cfme.common.vm_views import ProviderAllVMsView
from cfme.infrastructure.cluster import ClusterDetailsView
from cfme.infrastructure.cluster import ProviderAllClustersView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import HostTemplatesOnlyAllView
from cfme.infrastructure.virtual_machines import ProviderTemplatesOnlyAllView
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.networks.provider import NetworkProvider
from cfme.networks.views import NetworkProviderDetailsView
from cfme.networks.views import ProviderSecurityGroupAllView
from cfme.storage.manager import ProviderStorageManagerAllView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator


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
    ("Availability Zones", ProviderAvailabilityZoneAllView),
    ("Cloud Tenants", ProviderTenantAllView),
    ("Flavors", ProviderFlavorAllView),
    ("Security Groups", ProviderSecurityGroupAllView),
    ("Instances", CloudProviderInstancesView),
    ("Images", CloudProviderImagesView),
    ("Orchestration Stacks", ProviderStackAllView),
    ("Storage Managers", ProviderStorageManagerAllView)
]
# TODO: add Host Aggregates view to CLOUD_PROVIDER_RELATIONSHIPS

# tuples of (collection_key, item_class) for parametrization
# if item_class is none the collection instance is looked up against appliance using collection_key
cloud_test_items = [
    "cloud_instances",
    "cloud_flavors",
    "cloud_av_zones",
    "cloud_tenants",
    "cloud_images",
    "security_groups",
    "cloud_stacks",
    "block_managers",
    "network_providers"
]

infra_test_items = [
    "clusters",
    "hosts",
    "datastores",
    "infra_vms",
    "infra_templates"
]


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
        if cluster_name == "None":
            pytest.skip(f"Host {host.name} is not a clustered host")
        obj = cluster_col.instantiate(name=cluster_name, provider=provider)
    elif relationship in ["Datastores", "VMs", "Templates"]:
        obj = kwargs.get("host")
    elif relationship == "Network Manager":
        network_providers_col = appliance.collections.network_providers
        provider = kwargs.get("provider")
        view = navigate_to(provider, "Details")  # resetter selects summary view
        network_prov_name = view.entities.summary("Relationships").get_text_of("Network Manager")
        obj = network_providers_col.instantiate(prov_class=NetworkProvider, name=network_prov_name)
    return obj


@pytest.fixture
def host(appliance, provider):
    host_collection = provider.hosts
    return random.choice(host_collection.all())


@test_requirements.relationships
@pytest.mark.parametrize("relationship,view", HOST_RELATIONSHIPS,
    ids=[rel[0] for rel in HOST_RELATIONSHIPS])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE)
def test_host_relationships(appliance, provider, setup_provider, host, relationship, view):
    """Tests relationship navigation for a host

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        tags: relationship
    """
    host_view = navigate_to(host, "Details")
    if host_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip(f"There are no relationships for {relationship}")
    obj = get_obj(relationship, appliance, provider=provider, host=host)
    host_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed


@test_requirements.relationships
@pytest.mark.parametrize("relationship,view", INFRA_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in INFRA_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([InfraProvider], selector=ONE_PER_TYPE)
def test_infra_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for an infrastructure provider

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/10h
        tags: relationship
    """
    provider_view = navigate_to(provider, "Details")  # resetter selects summary view
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip(f"There are no relationships for {relationship}")
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': provider})
    assert relationship_view.is_displayed


@test_requirements.relationships
@pytest.mark.parametrize("relationship, view", CLOUD_PROVIDER_RELATIONSHIPS,
    ids=[rel[0] for rel in CLOUD_PROVIDER_RELATIONSHIPS])
@pytest.mark.provider([CloudProvider], selector=ONE_PER_TYPE)
def test_cloud_provider_relationships(appliance, provider, setup_provider, relationship, view):
    """Tests relationship navigation for a cloud provider

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/8h
        tags: relationship
    """
    # Version dependent strings
    provider_view = navigate_to(provider, "Details")  # resetter selects summary view
    if provider_view.entities.summary("Relationships").get_text_of(relationship) == "0":
        pytest.skip(f"There are no relationships for {relationship}")
    obj = get_obj(relationship, appliance, provider=provider)
    provider_view.entities.summary("Relationships").click_at(relationship)
    relationship_view = appliance.browser.create_view(view, additional_context={'object': obj})
    assert relationship_view.is_displayed


@pytest.fixture(scope='function')
def prov_child_visibility(appliance, provider, request, tag, user_restricted):
    def _prov_child_visibility(relationship, visibility):
        provider.add_tag(tag=tag)
        rel_cls = getattr(appliance.collections, relationship)
        actual_visibility = _check_actual_visibility(rel_cls)

        @request.addfinalizer
        def _finalize():
            provider.remove_tag(tag=tag)

        if not actual_visibility:
            pytest.skip(f"There are no relationships for {relationship}")

        with user_restricted:
            actual_visibility = _check_actual_visibility(rel_cls)

        assert actual_visibility == visibility

    def _check_actual_visibility(item_cls):
        try:
            view = navigate_to(item_cls, 'All')
        except NavigationDestinationNotFound:
            view = navigate_to(item_cls.parent, 'All')
        try:
            if hasattr(view.entities, 'entity_names'):
                assert view.entities.entity_names
            else:
                # this case is specified for block_managers
                assert view.entities.read()
            actual_visibility = True
        except AssertionError:
            actual_visibility = False
        return actual_visibility

    return _prov_child_visibility


@test_requirements.tag
@pytest.mark.parametrize("relationship", infra_test_items)
@pytest.mark.provider([VMwareProvider], selector=ONE)
# used VMwareProvider to cover all relationship as they have each of them
def test_tagvis_infra_provider_children(prov_child_visibility, setup_provider, relationship):
    """ Tests that provider child's should not be visible for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to provider
        2. Login as restricted user, providers child not visible for user

    Polarion:
        assignee: prichard
        casecomponent: Tagging
        initialEstimate: 1/4h
    """
    prov_child_visibility(relationship, visibility=False)


@test_requirements.tag
@pytest.mark.parametrize("relationship", cloud_test_items)
@pytest.mark.provider(classes=[OpenStackProvider, EC2Provider], selector=ONE)
def test_tagvis_cloud_provider_children(prov_child_visibility, setup_provider, relationship):
    """ Tests that provider child's should not be visible for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Polarion:
        assignee: prichard
        initialEstimate: 1/8h
        casecomponent: Cloud
        caseimportance: high
        testSteps:
            1. As admin add tag to provider
            2. Login as restricted user, providers child not visible for user
    """
    prov_child_visibility(relationship, visibility=False)


@test_requirements.relationships
@pytest.mark.provider([CloudProvider, InfraProvider])
@pytest.mark.tier(1)
@pytest.mark.meta(
    blockers=[
        BZ(
            1756984,
            forced_streams=["5.11"],
            unblock=lambda provider: not provider.one_of(AzureProvider),
        )
    ]
)
@pytest.mark.meta(automates=[1353285])
def test_provider_refresh_relationship(provider, setup_provider):
    """Tests provider refresh

    Bugzilla:
        1353285
        1756984

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: relationship
    """
    result = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=[r".*ERROR.*"])
    result.start_monitoring()
    provider.refresh_provider_relationships(method='ui', wait=600)
    assert result.validate(wait="60s")


@test_requirements.relationships
@pytest.mark.provider([InfraProvider])
def test_host_refresh_relationships(provider, setup_provider):
    """ Test that host refresh doesn't fail

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: relationship
        testSteps:
            1. Go to a host summary page in cfme
            2. From configuration -> select "Refresh Relationships and Power State"
            3. No error, host inventory properly refreshes

    Bugzilla:
        1658240
    """
    host = provider.hosts.all()[0]
    host.refresh(cancel=True)
    provider.wait_for_relationship_refresh()


@pytest.mark.provider([InfraProvider])
@pytest.mark.meta(automates=[BZ(1732349)])
def test_template_refresh_relationships(appliance, provider, setup_provider):
    """ Test that template refresh doesn't fail

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/8h
        tags: relationship

    Bugzilla:
        1732349
    """
    # TODO(ghubale@redhat.com): Update this test case with navigation to details page of template
    templates_view = navigate_to(provider, 'ProviderTemplates')
    template_names = templates_view.entities.entity_names
    template_collection = appliance.provider_based_collection(provider=provider,
                                                              coll_type='templates')

    template = template_collection.instantiate(template_names[0], provider)
    template.refresh_relationships()
    provider.wait_for_relationship_refresh()


@pytest.mark.manual
@test_requirements.azure
@pytest.mark.tier(1)
def test_inventory_refresh_westindia_azure():
    """
    Bugzilla:
        1473619

    Polarion:
        assignee: anikifor
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@test_requirements.relationships
@pytest.mark.meta(automates=[1524443])
@pytest.mark.tier(1)
@pytest.mark.provider([AzureProvider], scope='function',
                      required_fields=[["provisioning", "image"]])
def test_change_network_security_groups_per_page_items(setup_provider, appliance, provider):
    """
    Bugzilla:
        1524443

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1/12h
        tags: relationship
        testSteps:
            1.Open Azure provider details view.
            2.Open Azure Network Manager
            3.Select Network Security Groups
            4.Change items per page
    """
    view = navigate_to(provider, "NetworkSecurityGroup")
    view.toolbar.view_selector.select('List View')
    total_count = view.paginator.items_amount
    for item_count in [5, 10, 20, 50, 100, 200, 500, 1000]:
        if item_count <= total_count:
            view.paginator.set_items_per_page(item_count)
            assert len(view.entities.get_all()) <= view.paginator.items_per_page
        else:
            break


@pytest.fixture(scope="function")
def custom_testing_vm(appliance, request, provider):
    """Fixture to provision vm
    Note: Need to use windows template to make sure `Extract Running process` works.
    """

    def _testing_vm(template_name):
        vm_name = random_vm_name("pwr-c")
        vm = appliance.collections.infra_vms.instantiate(
            vm_name, provider, template_name=template_name
        )

        if not provider.mgmt.does_vm_exist(vm.name):
            logger.info("deploying %s on provider %s", vm.name, provider.key)
            vm.create_on_provider(allow_skip="default", find_in_cfme=True)
        request.addfinalizer(vm.cleanup_on_provider)
        return vm

    return _testing_vm


@test_requirements.relationships
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1729953])
@pytest.mark.provider([RHEVMProvider], selector=ONE)
def test_datastore_relationships(setup_provider, full_template, custom_testing_vm):
    """
    Bugzilla:
        1729953

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        tags: relationship
        setup:
            1. Add infrastructure provider(e.g: vsphere65)
            2. Provision VM
            3. Setup SSA
        testSteps:
            1. Navigate to VM's details page and click on 'Datastores' from 'Relationships' table
            2. Click on 'Managed VMs' from 'Relationships' table
            3. Select VM(Vm should be in 'on' state) and perform operations(Refresh Relationships
               and Power States, Perform Smartstate Analysis, Extract Running Processes) by
               selecting from 'configuration' dropdown
        expectedResults:
            1.
            2.
            3. Operations should be performed successfully. It should not give unexpected error.
    """
    testing_vm = custom_testing_vm(full_template.name)
    view = navigate_to(testing_vm.datastore, "ManagedVMs")
    view.entities.get_entity(name=testing_vm.name).check()

    view.toolbar.configuration.item_select(
        "Refresh Relationships and Power States", handle_alert=True
    )
    view.flash.assert_success_message(
        "Refresh Provider initiated for 1 VM and Instance from the CFME Database"
    )
    view.flash.dismiss()

    view.toolbar.configuration.item_select("Perform SmartState Analysis", handle_alert=True)
    view.flash.assert_success_message(
        "Analysis initiated for 1 VM and Instance from the CFME Database"
    )
    view.flash.dismiss()

    view.toolbar.configuration.item_select("Extract Running Processes", handle_alert=True)
    view.flash.assert_no_error()


@pytest.fixture(scope="function")
def cluster(provider):
    collection = provider.appliance.collections.clusters
    try:
        cluster_name = provider.data["cap_and_util"]["cluster"]
    except KeyError:
        pytest.skip(f"Unable to identify cluster for provider: {provider}")

    return collection.instantiate(name=cluster_name, provider=provider)


@test_requirements.relationships
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1732370])
@pytest.mark.provider([InfraProvider], selector=ONE)
def test_ssa_cluster_relationships(setup_provider, cluster, custom_testing_vm, win2012_template):
    """
    Bugzilla:
        1732370

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/12h
        tags: relationship
        setup:
            1. Setup SSA
        testSteps:
            1. Add infra provider
            2. Go to it's details page
            3. Click on 'All VMs' from 'Relationships' table
            4. Select any vm and click on options like 'Refresh Relationships and Power states' or
              'perform smartstate analysis' and 'Extract running processes' from 'configuration'
        expectedResults:
            1.
            2.
            3.
            4. Operations should be performed successfully. It should not give unexpected error.
    """
    testing_vm = custom_testing_vm(win2012_template.name)
    view = navigate_to(cluster, "AllVMs")
    view.entities.get_entity(name=testing_vm.name, surf_pages=True).check()

    view.toolbar.configuration.item_select(
        "Refresh Relationships and Power States", handle_alert=True
    )
    view.flash.assert_success_message(
        "Refresh Provider initiated for 1 VM and Instance from the CFME Database"
    )
    view.flash.dismiss()

    view.toolbar.configuration.item_select("Perform SmartState Analysis", handle_alert=True)
    view.flash.assert_success_message(
        "Analysis initiated for 1 VM and Instance from the CFME Database"
    )
    view.flash.dismiss()

    view.toolbar.configuration.item_select("Extract Running Processes", handle_alert=True)
    view.flash.assert_success_message(
        "Collect Running Processes initiated for 1 VM and Instance from the CFME Database"
    )
    view.flash.dismiss()
