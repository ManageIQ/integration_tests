"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import (
    dportgroup_template,
    dual_disk_template,
    dual_network_template,
    rhel69_template,
    rhel7_minimal,
    ubuntu16_template,
    win7_template,
    win10_template,
    win2016_template,
    win2012_template,
)
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider], selector=ONE_PER_VERSION, required_flags=["v2v"], scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_providers", "host_creds", "conversion_tags"),
]


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns the migrated_vm obj from target_provider."""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore",
    [
        ["nfs", "nfs", rhel7_minimal],
        ["nfs", "iscsi", rhel7_minimal],
        ["iscsi", "iscsi", rhel7_minimal],
        ["iscsi", "nfs", rhel7_minimal],
        ["iscsi", "local", rhel7_minimal],
    ],
    indirect=True,
)
def test_single_datastore_single_vm_migration(
    request, appliance, provider, form_data_vm_obj_single_datastore
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = form_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    # validate MAC address matches between source and target VMs
    assert migration_plan.is_migration_complete(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(src_vm_obj, provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    "form_data_vm_obj_single_network",
    [["DPortGroup", "ovirtmgmt", dportgroup_template], ["VM Network", "ovirtmgmt", rhel7_minimal]],
    indirect=True,
)
def test_single_network_single_vm_migration(
    request, appliance, provider, form_data_vm_obj_single_network
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    # This test will make use of migration request details page to track status of migration
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_network.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_network.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    request_details_list = migration_plan.migration_plan_request(migration_plan.name)
    vms = request_details_list.read()
    assert (len(vms) > 0 and
            request_details_list.is_successful(vms[0]) and
            not request_details_list.is_errored(vms[0]))
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_network.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, provider)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    "form_data_dual_vm_obj_dual_datastore",
    [[["nfs", "nfs", rhel7_minimal], ["iscsi", "iscsi", rhel7_minimal]]],
    indirect=True,
)
def test_dual_datastore_dual_vm_migration(
    request, appliance, provider, form_data_dual_vm_obj_dual_datastore, soft_assert
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_dual_vm_obj_dual_datastore.form_data
    )

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_dual_vm_obj_dual_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    request_details_list = migration_plan.migration_plan_request(migration_plan.name)
    vms = request_details_list.read()
    assert (len(vms) > 0 and
            request_details_list.is_successful(vms[0]) and
            not request_details_list.is_errored(vms[0]))

    src_vms_list = form_data_dual_vm_obj_dual_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm_obj(src_vm, provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    "form_data_vm_obj_dual_nics",
    [[["VM Network", "ovirtmgmt"], ["DPortGroup", "Storage - VLAN 33"], dual_network_template]],
    indirect=True,
)
def test_dual_nics_migration(request, appliance, provider, form_data_vm_obj_dual_nics):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_dual_nics.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_dual_nics.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    assert migration_plan.is_migration_complete(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_dual_nics.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, provider)
    assert set(src_vm.mac_address.split(", ")) == set(migrated_vm.mac_address.split(", "))


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", dual_disk_template]], indirect=True
)
def test_dual_disk_vm_migration(request, appliance, provider, form_data_vm_obj_single_datastore):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    assert migration_plan.is_migration_complete(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_datastore.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, provider)
    assert src_vm.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize(
    "form_data_multiple_vm_obj_single_datastore",
    [
        ["nfs", "nfs", [win7_template, win10_template]],
        ["nfs", "nfs", [win2016_template, rhel69_template]],
        ["nfs", "nfs", [win2012_template, ubuntu16_template]],
    ],
    indirect=True,
)
def test_migrations_different_os_templates(
    request, appliance, provider, form_data_multiple_vm_obj_single_datastore, soft_assert
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_multiple_vm_obj_single_datastore.form_data
    )

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_multiple_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    request_details_list = migration_plan.migration_plan_request(migration_plan.name)
    vms = request_details_list.read()
    assert (len(vms) > 0 and
            request_details_list.is_successful(vms[0]) and
            not request_details_list.is_errored(vms[0]))

    src_vms_list = form_data_multiple_vm_obj_single_datastore.vm_list
    # validate MAC address matches between source and target VMs
    for src_vm in src_vms_list:
        migrated_vm = get_migrated_vm_obj(src_vm, provider)
        soft_assert(src_vm.mac_address == migrated_vm.mac_address)


@pytest.mark.parametrize(
    "conversion_tags, form_data_vm_obj_single_datastore",
    [["SSH", ["nfs", "nfs", rhel7_minimal]]],
    indirect=True,
)
def test_single_vm_migration_with_ssh(
    request, appliance, provider, form_data_vm_obj_single_datastore
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    assert migration_plan.is_migration_complete(migration_plan.name)
    # validate MAC address matches between source and target VMs
    src_vm = form_data_vm_obj_single_datastore.vm_list.pop()
    migrated_vm = get_migrated_vm_obj(src_vm, provider)
    assert src_vm.mac_address == migrated_vm.mac_address
