"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest
from widgetastic.exceptions import WebDriverException

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import rhel69_template
from cfme.fixtures.templates import rhel7_minimal
from cfme.fixtures.templates import ubuntu16_template
from cfme.fixtures.templates import win7_template
from cfme.fixtures.v2v_fixtures import cleanup_target
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.fixtures.v2v_fixtures import infra_mapping_default_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.v2v,
    pytest.mark.provider(
        classes=[RHEVMProvider, OpenStackProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        fixture_name="target_provider",
        scope="module",
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        required_flags=["v2v"],
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.mark.parametrize('power_state', ['RUNNING', 'STOPPED'])
def test_single_vm_migration_power_state_tags_retirement(appliance, target_provider,
                                                         mapping_data_vm_obj_mini,
                                                         power_state):
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
    # Test VM migration power state and tags are preserved
    # as this is single_vm_migration it only has one vm_obj
    src_vm = mapping_data_vm_obj_mini.vm_list[0]
    if power_state not in src_vm.mgmt.state:
        if power_state == 'RUNNING':
            src_vm.mgmt.start()
        elif power_state == 'STOPPED':
            src_vm.mgmt.stop()
    tag = (appliance.collections.categories.instantiate(display_name='Owner *').collections.tags
        .instantiate(display_name='Production Linux Team'))
    src_vm.add_tag(tag)
    src_vm.set_retirement_date(offset={'hours': 1})

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        vm_list=mapping_data_vm_obj_mini.vm_list,
        target_provider=target_provider
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # check power state on migrated VM
    rhv_prov = target_provider
    migrated_vm = rhv_prov.mgmt.get_vm(src_vm.name)
    assert power_state in migrated_vm.state
    # check tags
    vm_obj = appliance.collections.infra_vms.instantiate(migrated_vm.name, rhv_prov)
    owner_tag = None
    for t in vm_obj.get_tags():
        if tag.display_name in t.display_name:
            owner_tag = t
    assert owner_tag is not None and tag.display_name in owner_tag.display_name
    # If Never is not there, that means retirement is set.
    assert 'Never' not in vm_obj.retirement_date


@pytest.mark.parametrize('mapping_data_multiple_vm_obj_single_datastore', [['nfs', 'nfs',
        [rhel7_minimal, ubuntu16_template, rhel69_template, win7_template]]], indirect=True)
def test_multi_host_multi_vm_migration(request, appliance, target_provider, soft_assert,
                                       mapping_data_multiple_vm_obj_single_datastore):
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
    mapping_data = mapping_data_multiple_vm_obj_single_datastore.infra_mapping_data
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=mapping_data_multiple_vm_obj_single_datastore.vm_list,
        target_provider=target_provider
    )

    assert migration_plan.wait_for_state("Started")

    request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
    vms = request_details_list.read()
    # testing multi-host utilization

    def _is_migration_started():
        for vm in vms:
            if 'Migrating' not in request_details_list.get_message_text(vm):
                return False
        return True

    wait_for(func=_is_migration_started, message="migration is not started for all VMs, "
             "be patient please", delay=5, num_sec=5400)
    host_creds = target_provider.hosts.all()
    hosts_dict = {key.name: [] for key in host_creds}
    for vm in vms:
        popup_text = request_details_list.read_additional_info_popup(vm)
        # open__additional_info_popup function also closes opened popup in our case
        request_details_list.open_additional_info_popup(vm)
        if popup_text['Conversion Host'] in hosts_dict:
            hosts_dict[popup_text['Conversion Host']].append(vm)
    for host in hosts_dict:
        if len(hosts_dict[host]) > 0:
            logger.info("Host: {} is migrating VMs: {}".format(host, hosts_dict[host]))
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")


def test_migration_special_char_name(appliance, target_provider, request,
                                     mapping_data_vm_obj_mini):
    """Tests migration where name of migration plan is comprised of special non-alphanumeric
       characters, such as '@#$(&#@('.

    Polarion:
        assignee: sshveta
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
        initialEstimate: 1h
    """

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        vm_list=mapping_data_vm_obj_mini.vm_list,
        target_provider=target_provider
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # validate MAC address matches between source and target VMs
    src_vm = mapping_data_vm_obj_mini.vm_list[0]
    migrated_vm = get_migrated_vm(src_vm, target_provider)

    @request.addfinalizer
    def _cleanup():
        cleanup_target(target_provider, migrated_vm)

    assert src_vm.mac_address == migrated_vm.mac_address


def test_migration_long_name(request, appliance, provider, target_provider, rhel7_minimal):
    """Test to check VM name with 64 character should work

    Polarion:
        assignee: sshveta
        initialEstimate: 1/2h
        casecomponent: V2V
    """
    source_datastores_list = provider.data.get("datastores", [])
    source_datastore = [d.name for d in source_datastores_list if d.type == "nfs"][0]
    collection = appliance.provider_based_collection(provider)

    # Following code will create vm name with 64 characters
    vm_name = "{vm_name}{extra_words}".format(vm_name=random_vm_name(context="v2v"),
                                              extra_words=fauxfactory.gen_alpha(51))
    vm_obj = collection.instantiate(
        name=vm_name,
        provider=provider,
        template_name=rhel7_minimal["name"],
    )
    vm_obj.create_on_provider(
        timeout=2400,
        find_in_cfme=True,
        allow_skip="default",
        datastore=source_datastore)
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    mapping_data = infra_mapping_default_data(provider, target_provider)

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="long_name_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_long_name{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=[vm_obj],
        target_provider=target_provider
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    migrated_vm = get_migrated_vm(vm_obj, target_provider)
    assert vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('mapping_data_vm_obj_single_datastore', [['nfs', 'nfs', rhel7_minimal]],
 indirect=True)
def test_migration_with_edited_mapping(request, appliance, target_provider, provider,
                                       mapping_data_vm_obj_single_datastore):
    """
        Test migration with edited infrastructure mapping.
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
    mapping_data = infra_mapping_default_data(provider, target_provider)
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    mapping.update(mapping_data_vm_obj_single_datastore.infra_mapping_data)
    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
        target_provider=target_provider)

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    migrated_vm = get_migrated_vm(src_vm_obj, target_provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(target_provider, migrated_vm)

    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore", [["nfs", "nfs", ubuntu16_template]], indirect=True)
def test_migration_restart(request, appliance, target_provider, mapping_data_vm_obj_single_datastore):
    """
    Test migration by restarting evmserverd in middle of the process

    Polarion:
        assignee: sshveta
        initialEstimate: 1h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: V2V
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
        target_provider=target_provider,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
    )
    view = navigate_to(migration_plan, "InProgress")
    assert migration_plan.wait_for_state("Started")

    def _system_reboot():
        # reboot system when migrated percentage greater than 20%
        ds_percent = int(view.progress_card.get_progress_percent(migration_plan.name)["datastores"])
        if ds_percent > 10:
            appliance.restart_evm_rude()
            return True
        else:
            return False

    # wait until system restarts
    wait_for(
        func=_system_reboot,
        message="migration plan is in progress, be patient please",
        delay=10,
        num_sec=1800
    )
    appliance.wait_for_web_ui()
    try:
        assert migration_plan.wait_for_state("In_Progress")
    except WebDriverException:
        pass
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")
    migrated_vm = get_migrated_vm(src_vm_obj, target_provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(target_provider, migrated_vm)

    assert src_vm_obj.mac_address == migrated_vm.mac_address
