"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest
from widgetastic.exceptions import WebDriverException

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.templates import _get_template
from cfme.fixtures.templates import Templates
from cfme.fixtures.v2v_fixtures import cleanup_target
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.fixtures.v2v_fixtures import infra_mapping_default_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for


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
        selector=ONE_PER_TYPE,
        required_flags=["v2v"],
        fixture_name="source_provider",
        scope="module",
    ),
    pytest.mark.usefixtures("v2v_provider_setup")
]


@pytest.mark.parametrize('power_state', ['RUNNING', 'STOPPED'])
@pytest.mark.uncollectif(
    lambda provider, power_state:
    provider.one_of(OpenStackProvider) and power_state == 'STOPPED',
    reason='VM state should not be stopped while migrating to Openstack provider.'
)
def test_single_vm_migration_power_state_tags_retirement(appliance, provider,
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
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        vm_list=mapping_data_vm_obj_mini.vm_list,
        target_provider=provider
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # check power state on migrated VM
    migrated_vm = get_migrated_vm(src_vm, provider)
    assert power_state in migrated_vm.mgmt.state
    # check tags
    collection = provider.appliance.provider_based_collection(provider)
    vm_obj = collection.instantiate(migrated_vm.name, provider)
    owner_tag = None
    for t in vm_obj.get_tags():
        if tag.display_name in t.display_name:
            owner_tag = t
    assert owner_tag is not None and tag.display_name in owner_tag.display_name
    # If Never is not there, that means retirement is set.
    assert 'Never' not in vm_obj.retirement_date


@pytest.mark.parametrize('source_type, dest_type, template_type',
                         [
                             ['nfs', 'nfs', [Templates.RHEL7_MINIMAL,
                                             Templates.RHEL7_MINIMAL,
                                             Templates.RHEL7_MINIMAL,
                                             Templates.RHEL7_MINIMAL]
                              ]
                         ])
def test_multi_host_multi_vm_migration(request, appliance, provider,
                                       source_type, dest_type, template_type,
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
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        vm_list=mapping_data_multiple_vm_obj_single_datastore.vm_list,
        target_provider=provider
    )

    assert migration_plan.wait_for_state("Started")

    request_details_list = migration_plan.get_plan_vm_list(wait_for_migration=False)
    vms = request_details_list.read()
    # testing multi-host utilization

    match = ['Converting', 'Migrating']

    def _is_migration_started(vm):
        if any(string in request_details_list.get_message_text(vm) for string in match):
            return True
        return False

    for vm in vms:
        wait_for(func=_is_migration_started, func_args=[vm],
            message="migration has not started for all VMs", delay=5, num_sec=300)

    if provider.one_of(OpenStackProvider):
        host_creds = provider.appliance.collections.openstack_nodes.all()
    else:
        host_creds = provider.hosts.all()

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


def test_migration_special_char_name(appliance, provider, request,
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
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(start="plan_desc_"),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        vm_list=mapping_data_vm_obj_mini.vm_list,
        target_provider=provider
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # validate MAC address matches between source and target VMs
    src_vm = mapping_data_vm_obj_mini.vm_list[0]
    migrated_vm = get_migrated_vm(src_vm, provider)

    @request.addfinalizer
    def _cleanup():
        cleanup_target(provider, migrated_vm)

    assert src_vm.mac_address == migrated_vm.mac_address


def test_migration_long_name(request, appliance, provider, source_provider):
    """Test to check VM name with 64 character should work

    Polarion:
        assignee: sshveta
        initialEstimate: 1/2h
        casecomponent: V2V
    """
    source_datastores_list = source_provider.data.get("datastores", [])
    source_datastore = [d.name for d in source_datastores_list if d.type == "nfs"][0]
    collection = appliance.provider_based_collection(source_provider)

    # Following code will create vm name with 64 characters
    vm_name = "{vm_name}{extra_words}".format(vm_name=random_vm_name(context="v2v"),
                                              extra_words=fauxfactory.gen_alpha(51))
    template = _get_template(source_provider, Templates.RHEL7_MINIMAL)
    vm_obj = collection.instantiate(
        name=vm_name,
        provider=source_provider,
        template_name=template.name,
    )
    vm_obj.create_on_provider(
        timeout=2400,
        find_in_cfme=True,
        allow_skip="default",
        datastore=source_datastore)
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    mapping_data = infra_mapping_default_data(source_provider, provider)

    infrastructure_mapping_collection = appliance.collections.v2v_infra_mappings
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(20, start="long_name_"),
        description=fauxfactory.gen_alphanumeric(25, start="desc_long_name_"),
        infra_map=mapping.name,
        vm_list=[vm_obj],
        target_provider=provider
    )
    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    migrated_vm = get_migrated_vm(vm_obj, provider)
    assert vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.parametrize('source_type, dest_type, template_type',
                         [['nfs', 'nfs', Templates.RHEL7_MINIMAL]])
def test_migration_with_edited_mapping(request, appliance, source_provider, provider,
                                       source_type, dest_type, template_type,
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
    mapping_data = infra_mapping_default_data(source_provider, provider)
    mapping = infrastructure_mapping_collection.create(**mapping_data)

    mapping.update(mapping_data_vm_obj_single_datastore.infra_mapping_data)
    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = mapping_data_vm_obj_single_datastore.vm_list[0]

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        vm_list=mapping_data_vm_obj_single_datastore.vm_list,
        target_provider=provider)

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


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "source_type, dest_type, template_type",
    [["nfs", "nfs", Templates.UBUNTU16_TEMPLATE]])
def test_migration_restart(request, appliance, provider,
                           source_type, dest_type, template_type,
                           mapping_data_vm_obj_single_datastore):
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
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(15, start="plan_desc_"),
        infra_map=mapping.name,
        target_provider=provider,
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
    migrated_vm = get_migrated_vm(src_vm_obj, provider)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)
        cleanup_target(provider, migrated_vm)

    assert src_vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.tier(2)
def test_if_no_password_is_exposed_in_logs_during_migration(appliance, source_provider, provider,
                                                            request, mapping_data_vm_obj_mini):
    """
    title: OSP: Test if no password is exposed in logs during migration

    Polarion:
        assignee: mnadeem
        casecomponent: V2V
        initialEstimate: 1/8h
        startsin: 5.10
        subcomponent: OSP
        testSteps:
            1. Create infrastructure mapping for Vmware to OSP/RHV
            2. Create migration plan
            3. Start migration
        expectedResults:
            1. Mapping created and visible in UI
            2.
            3. logs should not show password during migration
    """
    cred = []
    ssh_key_name = source_provider.data['private-keys']['vmware-ssh-key']['credentials']
    cred.append(credentials[source_provider.data.get("credentials")]["password"])
    cred.append(credentials[ssh_key_name]["password"])
    cred.append(credentials[provider.data.get("credentials")]["password"])
    if provider.one_of(OpenStackProvider):
        osp_key_name = provider.data['private-keys']['conversion_host_ssh_key']['credentials']
        cred.append(credentials[osp_key_name]["password"])

    automation_log = LogValidator("/var/www/miq/vmdb/log/automation.log", failure_patterns=cred,
                           hostname=appliance.hostname)
    evm_log = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=cred,
                           hostname=appliance.hostname)

    automation_log.start_monitoring()
    evm_log.start_monitoring()

    migration_plan_collection = appliance.collections.v2v_migration_plans
    migration_plan = migration_plan_collection.create(
        name=fauxfactory.gen_alphanumeric(start="plan_"),
        description=fauxfactory.gen_alphanumeric(start="plan_desc_"),
        infra_map=mapping_data_vm_obj_mini.infra_mapping_data.get("name"),
        vm_list=mapping_data_vm_obj_mini.vm_list,
        target_provider=provider
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    src_vm = mapping_data_vm_obj_mini.vm_list[0]
    migrated_vm = get_migrated_vm(src_vm, provider)

    @request.addfinalizer
    def _cleanup():
        cleanup_target(provider, migrated_vm)
        migration_plan.delete_completed_plan()

    # Check log files for any exposed password
    assert automation_log.validate()
    assert evm_log.validate()
