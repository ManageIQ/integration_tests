import fauxfactory
import pytest

from cfme import test_requirements
from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.utils.conf import credentials


pytestmark = [
    pytest.mark.ignore_stream("5.8"),
    test_requirements.ansible,
    pytest.mark.meta(
        server_roles=["+embedded_ansible"]
    ),
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"]
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name="second_provider",
        required_flags=["v2v"],
    ),
]

REPOSITORIES = "https://github.com/v2v-test/ansible_playbooks.git"


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns the migrated_vm obj from target_provider."""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm

@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.fixture(scope="module")
def action_collection(appliance):
    return appliance.collections.actions


@pytest.fixture(scope="module")
def credentials_collection(appliance):
    return appliance.collections.ansible_credentials


@pytest.fixture(scope="module")
def ansible_repository(appliance):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        fauxfactory.gen_alpha(), REPOSITORIES, description=fauxfactory.gen_alpha()
    )
    view = navigate_to(repository, "Details")
    if appliance.version < "5.9":
        refresh = view.browser.refresh
    else:
        refresh = view.toolbar.refresh.click
    wait_for(
        lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
        timeout=60,
        fail_func=refresh,
    )
    yield repository

    if repository.exists:
        repository.delete()


def catalog_item(request, appliance, machine_credential, ansible_repository, playbook_type):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "{}.yml".format(playbook_type),
            "machine_credential": machine_credential,
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric(),
        },
    )

    @request.addfinalizer
    def _cleanup():
        if cat_item.exists:
            cat_item.delete()
    return cat_item


@pytest.mark.parametrize(
    "form_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migration_playbooks(request, appliance, wait_for_ansible, ansible_repository,
            credentials_collection, v2v_providers, host_creds, conversion_tags,
                             form_data_vm_obj_single_datastore):
    """Test for migrating vms with pre and post playbooks"""
    CREDENTIALS = (
        "Machine",
        {
            "username": credentials[
                v2v_providers.vmware_provider.data.templates.get("rhel7_minimal").creds].username,
            "password": credentials[
                v2v_providers.vmware_provider.data.templates.get("rhel7_minimal").creds].password,
            "privilage_escalation": "sudo",
        },
    )
    credential = credentials_collection.create(
        name="{}_credential_{}".format(CREDENTIALS[0], fauxfactory.gen_alpha()),
        credential_type=CREDENTIALS[0],
        **CREDENTIALS[1]
    )

    provision_catalog = catalog_item(
        request, appliance, credential.name, ansible_repository, "provision")
    retire_catalog = catalog_item(
        request, appliance, credential.name, ansible_repository, "retire")

    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(
        form_data_vm_obj_single_datastore.form_data
    )

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
        pre_playbook=provision_catalog.name,
        post_playbook=retire_catalog.name,
    )

    # explicit wait for spinner of in-progress status car
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, "All").VIEW
    )
    wait_for(
        func=view.progress_card.is_plan_started,
        func_args=[migration_plan.name],
        message="migration plan is starting, be patient please",
        delay=5,
        num_sec=150,
        handle_exception=True,
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=5,
        num_sec=1800,
    )

    view.migr_dropdown.item_select("Completed Plans")
    view.wait_displayed()
    logger.info(
        "For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name),
    )
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(src_vm_obj, v2v_providers.rhv_provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address
