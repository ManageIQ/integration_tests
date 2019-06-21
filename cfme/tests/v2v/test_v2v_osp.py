"""Tests to validate openstack provider related usecases"""
import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.provider(
        classes=[OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    test_requirements.v2v,
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.mark.parametrize("project", ["default", "secondary"])
@pytest.mark.parametrize("attribute", ["flavor", "security_group"])
@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True)
def test_v2v_custom_project_attribute(
        request, appliance, provider, project, attribute, mapping_data_vm_obj_single_datastore):
    """
    Test V2V with custom attributes of openstack provider projects

    Polarion:
        assignee: ytale
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data

    if project == "secondary":
        # Changing target cluster (openstack project) to other than default
        component = mapping_data["clusters"][0].targets
        component.targets.pop()
        component.targets.append(partial_match(provider.data.clusters[1]))
        map_cluster = component.targets[1]

    mapping = infrastructure_mapping_collection.create(**mapping_data)
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    # Selecting default flavor and security group selection
    map_flavor = provider.data.flavors[0]
    map_security_group = provider.data.security_groups.admin[0]

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # Selecting second flavor and security group selection since first is default
    if attribute == "flavor":
        map_flavor = provider.data.flavors[1]
    else:
        map_security_group = provider.data.security_groups.admin[1]

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        osp_security_group=map_security_group,
        osp_flavor=map_flavor,
        target_provider=provider,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")
    migrated_vm = get_migrated_vm(src_vm_obj, provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address

    osp_server = provider.mgmt.get_vm(name=src_vm_obj.name)
    # Test1: Checking map's flavor with openstack server flavor
    assert map_flavor == osp_server.flavor.name
    # Test2: Checking map's security group with openstack server security group
    assert map_security_group == osp_server.security_groups[0]

    if project == "secondary":
        new_view = navigate_to(src_vm_obj, "Details")
        osp_project = new_view.entities.summary("Relationships").get_text_of("Cloud Tenants")
        assert map_cluster == osp_project
