import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.fixtures.provider import rhel7_minimal
from cfme.fixtures.v2v_fixtures import get_migrated_vm
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.wait import wait_for
from cfme.v2v.migration_plans import MigrationPlanRequestDetailsView


pytestmark = [
    test_requirements.v2v,
    pytest.mark.meta(
        server_roles=["+embedded_ansible"]
    ),
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
        scope="module"
    ),
    pytest.mark.usefixtures("v2v_provider_setup"),
]


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


@pytest.mark.parametrize(
    "mapping_data_vm_obj_single_datastore", [["nfs", "nfs", rhel7_minimal]], indirect=True
)
def test_migration_playbooks(request, appliance, source_provider, provider,
                             ansible_repository, mapping_data_vm_obj_single_datastore):
    """
    Test for migrating vms with pre and post playbooks

    Polarion:
        assignee: sshveta
        caseimportance: medium
        caseposneg: positive
        casecomponent: V2V
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        testSteps:
            1. Enable embedded ansible role
            2. Create repository
            3. Create credentials
            4. Create ansible catalog item with provision.yml playbook
            5. Create ansible catalog item with retire.yml playbook
            6. Migrate VM from vmware to RHV/OSP using the above catalog items
    """
    try:
        creds = credentials[source_provider.data.templates.get('rhel7_minimal', {})['creds']]
    except KeyError:
        pytest.skip("Credentials not found for template")

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
        target_provider=provider,
        pre_playbook=provision_catalog.name,
        post_playbook=retire_catalog.name,
        pre_checkbox=True,
        post_checkbox=True
    )

    assert migration_plan.wait_for_state("Started")
    assert migration_plan.wait_for_state("In_Progress")
    assert migration_plan.wait_for_state("Completed")
    assert migration_plan.wait_for_state("Successful")

    # Downloading pre and post migration logs
    view = navigate_to(migration_plan, "CompletedPlanDetails")
    view.download_logs.item_select("Premigration log")
    view.flash.assert_no_error()
    view.download_logs.item_select("Postmigration log")
    view.flash.assert_no_error()

    migrated_vm = get_migrated_vm(src_vm_obj, provider)
    assert src_vm_obj.mac_address == migrated_vm.mac_address
