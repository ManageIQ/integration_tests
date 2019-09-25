"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import dportgroup_template
from cfme.fixtures.provider import dual_disk_template
from cfme.fixtures.provider import dual_network_template
from cfme.fixtures.provider import rhel69_template
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.provider import ubuntu16_template
from cfme.fixtures.provider import win10_template
from cfme.fixtures.provider import win2012_template
from cfme.fixtures.provider import win2016_template
from cfme.fixtures.provider import win7_template
from cfme.fixtures.v2v_fixtures import cleanup_target
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.blockers import BZ

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


@pytest.mark.meta(blockers=[BZ(1751900, forced_streams=['5.10'])])
@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore",
    [
        ["nfs", "iscsi", rhel7_minimal],
        ["iscsi", "iscsi", rhel7_minimal],
        ["iscsi", "nfs", rhel7_minimal],
        ["local", "nfs", rhel7_minimal],
    ],
    indirect=True,
)
@pytest.mark.uncollectif(
    lambda source_provider, mapping_data_vm_obj_single_datastore:
    source_provider.version == 6.5 and "local" in mapping_data_vm_obj_single_datastore
)
def test_single_datastore_single_vm_migration(
    request, appliance, provider, mapping_data_vm_obj_single_datastore
):
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
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]
    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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
    "mapping_data_vm_obj_single_network",
    [["DPortGroup", "ovirtmgmt", dportgroup_template], ["VM Network", "ovirtmgmt", rhel7_minimal]],
    indirect=True,
)
@pytest.mark.uncollectif(
    lambda source_provider, mapping_data_vm_obj_single_network:
    source_provider.version != 6.5 and "DPortGroup" in mapping_data_vm_obj_single_network
)
def test_single_network_single_vm_migration(
    request, appliance, provider, mapping_data_vm_obj_single_network
):
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
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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


@pytest.mark.parametrize(
    "mapping_data_dual_vm_obj_dual_datastore",
    [[["nfs", "nfs", rhel7_minimal], ["iscsi", "iscsi", rhel7_minimal]]],
    indirect=True,
)
def test_dual_datastore_dual_vm_migration(
    request, appliance, provider, mapping_data_dual_vm_obj_dual_datastore, soft_assert
):
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

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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
        request.addfinalizer(cleanup_target(provider, migrated_vm))
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    "mapping_data_vm_obj_dual_nics",
    [
        ["VM Network", "ovirtmgmt", dual_network_template],
        ["DPortGroup", "Storage - VLAN 33", dual_network_template]
    ],
    indirect=True,
)
@pytest.mark.uncollectif(
    lambda source_provider, mapping_data_vm_obj_dual_nics:
    source_provider.version != 6.5 and "DPortGroup" in mapping_data_vm_obj_dual_nics
)
def test_dual_nics_migration(request, appliance, provider, mapping_data_vm_obj_dual_nics):
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
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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
    "mapping_data_vm_obj_single_datastore", [["nfs", "nfs", dual_disk_template]], indirect=True
)
def test_dual_disk_vm_migration(
    request, appliance, provider, mapping_data_vm_obj_single_datastore
):
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
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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
    "mapping_data_multiple_vm_obj_single_datastore",
    [
        ["nfs", "nfs", [win7_template]],
        ["nfs", "nfs", [win10_template]],
        ["nfs", "nfs", [win2016_template]],
        ["nfs", "nfs", [rhel69_template]],
        ["nfs", "nfs", [win2012_template]],
        ["nfs", "nfs", [ubuntu16_template]],
    ],
    indirect=True,
)
def test_migrations_different_os_templates(
    request, appliance, provider, mapping_data_multiple_vm_obj_single_datastore, soft_assert
):
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

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
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
        request.addfinalizer(cleanup_target(provider, migrated_vm))
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)
