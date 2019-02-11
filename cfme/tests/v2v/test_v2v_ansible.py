import fauxfactory
import pytest

from cfme import test_requirements
from cfme.fixtures.provider import rhel7_minimal
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION, ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.conf import cfme_data, credentials
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.ansible,
    pytest.mark.meta(
        server_roles=["+embedded_ansible"]
    ),
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION,
        required_flags=["v2v"],
        scope="module"
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_TYPE,
        fixture_name="source_provider",
        required_flags=["v2v"],
        scope="module"
    ),
]


def get_migrated_vm_obj(src_vm_obj, target_provider):
    """Returns migrated_vm obj from target_provider"""
    collection = target_provider.appliance.provider_based_collection(target_provider)
    migrated_vm = collection.instantiate(src_vm_obj.name, target_provider)
    return migrated_vm


@pytest.fixture(scope="module")
def ansible_repository(appliance):
    """Fixture to add ansible repository"""
    appliance.wait_for_embedded_ansible()
    repositories = appliance.collections.ansible_repositories
    try:
        repository = repositories.create(
            name=fauxfactory.gen_alpha(),
            url=cfme_data.ansible_links.playbook_repositories.v2v,
            description=fauxfactory.gen_alpha()
        )
    except KeyError:
        pytest.skip("Skipping since no such key found in yaml")
    view = navigate_to(repository, "Details")
    wait_for(lambda: view.entities.summary("Properties").get_text_of("Status") == "successful",
             delay=10,
             timeout=60,
             fail_func=view.toolbar.refresh.click)
    yield repository

    if repository.exists:
        repository.delete()


def catalog_item(request, appliance, machine_credential, ansible_repository, playbook_type):
    """Add provisioning and retire ansible catalog item"""
    cat_item = appliance.collections.catalog_items.create(
        catalog_item_class=appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
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


def test_migration_playbooks(request, appliance, v2v_providers, host_creds, conversion_tags,
                             ansible_repository, form_data_vm_map_obj_mini):
    """Test for migrating vms with pre and post playbooks"""
    creds = credentials[v2v_providers.vmware_provider.data.templates.get("rhel7_minimal").creds]
    CREDENTIALS = (
        "Machine",
        {
            "username": creds.username,
            "password": creds.password,
            "privilage_escalation": "sudo",
        },
    )
    credential = appliance.collections.ansible_credentials.create(
        name="{type}_credential_{cred}".format(type=CREDENTIALS[0], cred=fauxfactory.gen_alpha()),
        credential_type=CREDENTIALS[0],
        **CREDENTIALS[1]
    )

    provision_catalog = catalog_item(
        request, appliance, credential.name, ansible_repository, "provision"
    )
    retire_catalog = catalog_item(
        request, appliance, credential.name, ansible_repository, "retire"
    )

    src_vm_obj = form_data_vm_map_obj_mini.vm_list
    migration_plan_collection = appliance.collections.v2v_plans
    migration_plan = migration_plan_collection.create(
        name="plan_{}".format(fauxfactory.gen_alphanumeric()),
        description="desc_{}".format(fauxfactory.gen_alphanumeric()),
        infra_map=form_data_vm_map_obj_mini.map_obj.name,
        vm_list=[form_data_vm_map_obj_mini.vm_list],
        start_migration=True,
        pre_playbook=provision_catalog.name,
        post_playbook=retire_catalog.name,
    )

    # explicit wait for spinner of in-progress status card
    view = appliance.browser.create_view(
        navigator.get_class(migration_plan_collection, "All").VIEW.pick()
    )
    wait_for(
        func=view.progress_card.is_plan_started,
        func_args=[migration_plan.name],
        message="migration plan is starting, be patient please",
        delay=5,
        num_sec=280,
        handle_exception=True,
        fail_cond=False
    )

    # wait until plan is in progress
    wait_for(
        func=view.plan_in_progress,
        func_args=[migration_plan.name],
        message="migration plan is in progress, be patient please",
        delay=15,
        num_sec=3600,
    )
    view.switch_to("Completed Plans")
    view.wait_displayed()
    migration_plan_collection.find_completed_plan(migration_plan)
    logger.info(
        "For plan %s, migration status after completion: %s, total time elapsed: %s",
        migration_plan.name,
        view.migration_plans_completed_list.get_vm_count_in_plan(migration_plan.name),
        view.migration_plans_completed_list.get_clock(migration_plan.name),
    )

    # validate MAC address matches between source and target VMs
    assert view.migration_plans_completed_list.is_plan_succeeded(migration_plan.name)
    migrated_vm = get_migrated_vm_obj(src_vm_obj, v2v_providers.rhv_provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address
