import fauxfactory
import pytest
from widgetastic.widget import NoSuchElementException

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import rhel69_template
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.provider import ubuntu16_template
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.v2v.migration_settings import MigrationSettings

pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[OpenStackProvider, RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
]


@pytest.mark.parametrize(
    "mapping_data_multiple_vm_obj_single_datastore",
    [
        ["nfs", "nfs", [rhel7_minimal, rhel69_template, ubuntu16_template]],
    ],
    indirect=True,
)
def test_migration_throttling(
    request, appliance, provider, mapping_data_multiple_vm_obj_single_datastore
):
    """
    Polarion:
        assignee: sshveta
        casecomponent: V2V
        initialEstimate: 1/4h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
    """
    migration_settings = MigrationSettings(appliance)
    migration_settings.migration_throttling.set_max_migration_per_conv_host("2")

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping_data = mapping_data_multiple_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=mapping_data_multiple_vm_obj_single_datastore.vm_list,
    )
    assert migration_plan.wait_for_state("Started")
    request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
    vms = request_details_list.read()

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        request_details_list.cancel_migration(vm, confirmed=True)

    conversion_host_popup = []
    host_creds = provider.hosts.all()
    hosts_dict = {key.name: [] for key in host_creds}
    # Check if conversion host is shown for each VM
    for vm in vms:
        try:
            popup_text = request_details_list.read_additional_info_popup(vm)
            # open__additional_info_popup function also closes opened popup in our case
            request_details_list.open_additional_info_popup(vm)
            if popup_text['Conversion Host'] in hosts_dict:
                conversion_host_popup.append(popup_text['Conversion Host'])
        except NoSuchElementException:
            # conversion host might be empty for throttled vm
            # until it is waiting for other VM's to finish until BZ 1716283 is fixed.
            continue
    for conv_host in conversion_host_popup:
        # Not more than two VM's can have same conversion host
        assert (conversion_host_popup.count(conv_host) <= 2)
