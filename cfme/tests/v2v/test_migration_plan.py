"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import rhel7_minimal
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
    pytest.mark.usefixtures("v2v_provider_setup")
]


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns the migrated_vm obj from target_provider."""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore",
    [
        ["nfs", "nfs", rhel7_minimal]
    ],
    indirect=True,
)
def test_migration_plan(
    request, appliance, provider, mapping_data_vm_obj_single_datastore
):
    """
    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
    """
    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan_collection.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress()
    # validate MAC address matches between source and target VMs
    assert migration_plan.is_migration_complete()
    migrated_vm = get_migrated_vm_obj(src_vm_obj, provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address
