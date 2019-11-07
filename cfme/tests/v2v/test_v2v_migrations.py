"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import Templates
from cfme.fixtures.v2v_fixtures import cleanup_target
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
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
    pytest.mark.usefixtures("v2v_provider_setup"),
]


@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [
        ["nfs", "iscsi", Templates.RHEL7_MINIMAL],
        ["iscsi", "iscsi", Templates.RHEL7_MINIMAL],
        ["iscsi", "nfs", Templates.RHEL7_MINIMAL],
        ["local", "nfs", Templates.RHEL7_MINIMAL],
    ]
)
@pytest.mark.uncollectif(
    lambda source_provider, source_type:
    source_provider.one_of(VMwareProvider) and source_provider.version == 6.5 and
    "local" in source_type,
    reason='Single datastore of local and source provider version 6.5 not supported'
)
def test_single_datastore_single_vm_migration(request, appliance, provider,
                                              source_type, dest_type, template_type,
                                              mapping_data_vm_obj_single_datastore):
    """
    Test VM migration with single datastore
    Polarion:
        assignee: sshveta
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    migrated_vm = get_migrated_vm(src_vm_obj, provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(provider, migrated_vm)

    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [["DPortGroup", "ovirtmgmt", Templates.DPORTGROUP_TEMPLATE],
     ["VM Network", "ovirtmgmt", Templates.RHEL7_MINIMAL]]
)
@pytest.mark.uncollectif(
    lambda source_provider, source_type:
    source_provider.one_of(VMwareProvider) and source_provider.version != 6.5 and
    "DPortGroup" in source_type,
    reason='Single network of DPortGroup only supported on source provider version 6.5'
)
def test_single_network_single_vm_migration(request, appliance, provider,
                                            source_type, dest_type, template_type,
                                            mapping_data_vm_obj_single_network):
    """
    Polarion:
        assignee: sshveta
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_network.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_vm_obj_single_network.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    request_details_list = migration_plan.get_plan_vm_list()
    vms = request_details_list.read()
    assert len(vms) > 0, "No VMs displayed on Migration Plan Request Details list."
    assert request_details_list.is_successful(vms[0]) and not request_details_list.is_errored(
        vms[0]
    )
    # validate MAC address matches between source and target VMs
    src_vm = mapping_data_vm_obj_single_network.vm_list.pop()
    migrated_vm = get_migrated_vm(src_vm, provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(provider, migrated_vm)

    assert src_vm.mac_address == migrated_vm.mac_address


def test_dual_datastore_dual_vm_migration(request, appliance, provider,
                                          mapping_data_dual_vm_obj_dual_datastore,
                                          soft_assert):
    """
    Polarion:
        assignee: sshveta
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_dual_vm_obj_dual_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        for src_vm in src_vms_list:
            migrated_vm = get_migrated_vm(src_vm, provider)
            cleanup_target(provider, migrated_vm)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_dual_vm_obj_dual_datastore.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    request_details_list = migration_plan.get_plan_vm_list()
    vms = request_details_list.read()
    for vm in vms:
        soft_assert(
            request_details_list.is_successful(vm) and not request_details_list.is_errored(vm)
        )

    src_vms_list = mapping_data_dual_vm_obj_dual_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm(src_vm, provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [
        ["VM Network", "ovirtmgmt", Templates.DUAL_NETWORK_TEMPLATE],
        ["DPortGroup", "Storage - VLAN 33", Templates.DUAL_NETWORK_TEMPLATE]
    ],
)
@pytest.mark.uncollectif(
    lambda source_provider, source_type:
    source_provider.one_of(VMwareProvider) and source_provider.version != 6.5 and
    "DPortGroup" in source_type,
    reason='Dual network of DPortGroup only supported on source provider version 6.5'
)
def test_dual_nics_migration(request, appliance, provider,
                             source_type, dest_type, template_type,
                             mapping_data_vm_obj_dual_nics):
    """
    Polarion:
        assignee: sshveta
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_dual_nics.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_vm_obj_dual_nics.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")
    # validate MAC address matches between source and target VMs
    src_vm = mapping_data_vm_obj_dual_nics.vm_list.pop()
    migrated_vm = get_migrated_vm(src_vm, provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(provider, migrated_vm)

    assert set(src_vm.mac_address.split(", ")) == set(migrated_vm.mac_address.split(", "))


@pytest.mark.parametrize(
    "source_type, dest_type, template_type", [["nfs", "nfs", Templates.DUAL_DISK_TEMPLATE]]
)
def test_dual_disk_vm_migration(request, appliance, provider,
                                source_type, dest_type, template_type,
                                mapping_data_vm_obj_single_datastore):
    """
    Polarion:
        assignee: sshveta
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # validate MAC address matches between source and target VMs
    src_vm = mapping_data_vm_obj_single_datastore.vm_list.pop()
    migrated_vm = get_migrated_vm(src_vm, provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(provider, migrated_vm)

    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [
        ["nfs", "nfs", Templates.WIN7_TEMPLATE],
        ["nfs", "nfs", Templates.WIN10_TEMPLATE],
        ["nfs", "nfs", Templates.WIN2016_TEMPLATE],
        ["nfs", "nfs", Templates.RHEL69_TEMPLATE],
        ["nfs", "nfs", Templates.WIN2012_TEMPLATE],
        ["nfs", "nfs", Templates.UBUNTU16_TEMPLATE],
    ]
)
def test_migrations_different_os_templates(request, appliance, provider,
                                           source_type, dest_type, template_type,
                                           mapping_data_multiple_vm_obj_single_datastore,
                                           soft_assert):
    """
    Polarion:
        assignee: sshveta
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_multiple_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        for src_vm in src_vms_list:
            migrated_vm = get_migrated_vm(src_vm, provider)
            cleanup_target(provider, migrated_vm)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
        vm_list=mapping_data_multiple_vm_obj_single_datastore.vm_list,
    )
    request_details_list = migration_plan.get_plan_vm_list()
    vms = request_details_list.read()
    for vm in vms:
        soft_assert(
            request_details_list.is_successful(vm) and not request_details_list.is_errored(vm)
        )

    src_vms_list = mapping_data_multiple_vm_obj_single_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm(src_vm, provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)
