"""Test to validate End-to-End migrations- functional testing."""
import fauxfactory
import pytest

from cfme.fixtures.provider import (rhel7_minimal, ubuntu16_template,
 rhel69_template, win7_template)
from cfme.fixtures.v2v import _form_data
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider(
        classes=[RHEVMProvider], selector=ONE_PER_VERSION, required_flags=["v2v"], scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
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
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
@pytest.mark.parametrize("power_state", ["RUNNING", "STOPPED"])
def test_single_vm_migration_power_state_tags_retirement(
    request, appliance, provider, form_data_vm_obj_single_datastore, power_state
):
    """
    Polarion:
        assignee: kkulkarn
        casecomponent: V2V
        initialEstimate: 1/4h
        subcomponent: RHV
        upstream: yes
    """
    # Test VM migration power state and tags are preserved
    # as this is single_vm_migration it only has one vm_obj, which we extract on next line
    src_vm = form_data_vm_obj_single_datastore.vm_list[0]
    if power_state not in src_vm.mgmt.state:
        if power_state == "RUNNING":
            src_vm.mgmt.start()
        elif power_state == "STOPPED":
            src_vm.mgmt.stop()
    tag = appliance.collections.categories.instantiate(
        display_name="Owner *"
    ).collections.tags.instantiate(display_name="Production Linux Team")
    src_vm.add_tag(tag)
    src_vm.set_retirement_date(offset={"hours": 1})

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
    # check power state on migrated VM
    rhv_prov = provider
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
    assert "Never" not in vm_obj.retirement_date


@pytest.mark.parametrize(
    "form_data_multiple_vm_obj_single_datastore",
    [["nfs", "nfs", [rhel7_minimal, ubuntu16_template, rhel69_template, win7_template]]],
    indirect=True,
)
def test_multi_host_multi_vm_migration(
    request,
    appliance,
    providers,
    host_creds,
    soft_assert,
    form_data_multiple_vm_obj_single_datastore,
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
    # as migration is started, try to track progress using migration plan request details page

    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_request_shows_vm(migration_plan.name)
    view = appliance.browser.create_view(navigator.get_class(migration_plan, "Details").VIEW)
    view.wait_displayed()
    request_details_list = view.migration_request_details_list
    vms = request_details_list.read()
    view.items_on_page.item_select("15")
    # testing multi-host utilization

    def _is_migration_started():
        for vm in vms:
            if request_details_list.get_message_text(vm) != "Migrating":
                return False
        return True

    wait_for(
        func=_is_migration_started,
        message="migration is not started for all VMs, " "be patient please",
        delay=5,
        num_sec=600,
    )

    hosts_dict = {key.name: [] for key in host_creds}
    for vm in vms:
        popup_text = request_details_list.read_additional_info_popup(vm)
        # open__additional_info_popup function also closes opened popup in our case
        request_details_list.open_additional_info_popup(vm)
        if popup_text["Conversion Host"] in hosts_dict:
            hosts_dict[popup_text["Conversion Host"]].append(vm)
    for host in hosts_dict:
        logger.info("Host: {} is migrating VMs: {}".format(host, hosts_dict[host]))
        assert (
            len(hosts_dict[host]) > 0
        ), "Conversion Host: {} not being utilized for migration!".format(host)

    wait_for(
        func=view.plan_in_progress,
        message="migration plan is in progress, be patient please",
        delay=5,
        num_sec=14400,
    )

    for vm in vms:
        soft_assert(
            request_details_list.is_successful(vm) and not request_details_list.is_errored(vm)
        )


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migration_special_char_name(
    request, appliance, provider, form_data_vm_obj_single_datastore
):
    """Tests migration where name of migration plan is comprised of special non-alphanumeric
       characters, such as '@#$(&#@('.
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
    # fauxfactory.gen_special() used here to create special character string e.g. #$@#@
    migration_plan = migration_plan_collection.create(
        name="{}".format(fauxfactory.gen_special()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=form_data_vm_obj_single_datastore.vm_list,
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    assert migration_plan.is_migration_complete(migration_plan.name)
    src_vm = form_data_vm_obj_single_datastore.vm_list[0]
    migrated_vm = get_migrated_vm_obj(src_vm, provider)
    assert src_vm.mac_address == migrated_vm.mac_address


def test_migration_long_name(request, appliance, source_provider, provider):
    """Test to check VM name with 64 character should work
    Polarion:
        assignee: kkulkarn
        initialEstimate: 1/4h
    """
    source_datastores_list = source_provider.data.get("datastores", [])
    source_datastore = [d.name for d in source_datastores_list if d.type == "nfs"][0]
    collection = appliance.provider_based_collection(source_provider)

    # Following code will create vm name with 64 characters
    vm_name = "{vm_name}{extra_words}".format(
        vm_name=random_vm_name(context="v2v"), extra_words=fauxfactory.gen_alpha(51)
    )
    vm_obj = collection.instantiate(
        name=vm_name,
        provider=source_provider,
        template_name=rhel7_minimal(source_provider)["name"],
    )
    vm_obj.create_on_provider(
        timeout=2400, find_in_cfme=True, allow_skip="default", datastore=source_datastore
    )
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    form_data = _form_data(source_provider, provider)

    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="long_name_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_long_name{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=mapping.name,
        vm_list=[vm_obj],
        start_migration=True,
    )
    assert migration_plan.is_plan_started(migration_plan.name)
    assert migration_plan.is_plan_in_progress(migration_plan.name)
    assert migration_plan.is_migration_complete(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(vm_obj, provider)
    assert vm_obj.mac_address == migrated_vm.mac_address


@pytest.mark.ignore_stream("5.9")
@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migration_with_edited_mapping(
    request, appliance, provider, edited_form_data, form_data_vm_obj_single_datastore, soft_assert
):
    """
        Test migration with edited infrastructure mapping.
        Steps:
          * create mapping , edit mapping
          * Migrate vm
        Polarion:
            assignee: sshveta
            caseimportance: medium
            initialEstimate: 1/4h
        """
    _form_data, edited_form_data = edited_form_data
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_vm_obj_single_datastore.form_data)

    @request.addfinalizer
    def _cleanup():
        infrastructure_mapping_collection.delete(mapping)

    # vm_obj is a list, with only 1 VM object, hence [0]
    src_vm_obj = form_data_vm_obj_single_datastore.vm_list[0]

    mapping.update(edited_form_data)

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
    migrated_vm = get_migrated_vm_obj(src_vm_obj, provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address
