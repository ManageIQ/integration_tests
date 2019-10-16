import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.ansible import RemoteFile
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.tests.automate.custom_button import CredsHostsDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([VMwareProvider], selector=ONE, scope="module"),
]

INFRA_OBJECTS = [
    "PROVIDER",
    "HOSTS",
    "VM_INSTANCE",
    "TEMPLATE_IMAGE",
    "DATASTORES",
    "CLUSTERS",
    "SWITCH",
]

INVENTORY = ["Localhost", "Target Machine", "Specific Hosts"]


@pytest.fixture(
    params=INFRA_OBJECTS, ids=[obj.capitalize() for obj in INFRA_OBJECTS], scope="module"
)
def button_group(appliance, request):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(start="hvr_"),
        type=getattr(collection, request.param),
    )
    yield button_gp, request.param
    button_gp.delete_if_exists()


@pytest.fixture(scope="module")
def setup_obj(button_group, provider):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    try:
        if obj_type == "PROVIDER":
            obj = provider
        elif obj_type == "VM_INSTANCE":
            obj = provider.appliance.provider_based_collection(provider).all()[0]
        elif obj_type == "TEMPLATE_IMAGE":
            obj = provider.appliance.collections.infra_templates.all()[0]
        elif obj_type == "SWITCH":
            obj = provider.appliance.collections.infra_switches.all()[0]
        else:
            obj = getattr(provider.appliance.collections, obj_type.lower()).all()[0]
    except IndexError:
        pytest.skip(f"Object not found for {obj_type} type")

    return obj


@pytest.mark.meta(blockers=[BZ(1685555, unblock=lambda button_group: "SWITCH" not in button_group)])
@pytest.mark.parametrize("inventory", INVENTORY, ids=["_".join(item.split()) for item in INVENTORY])
@pytest.mark.uncollectif(
    lambda appliance, button_group, inventory: (
        "VM_INSTANCE" not in button_group and inventory == "Target Machine"
    )
    or (appliance.version < "5.11" and inventory == "Localhost")
)
def test_custom_button_ansible_automate_infra_obj(
    request, appliance, inventory, setup_obj, button_group, ansible_catalog_item_create_empty_file,
    target_machine, target_machine_ansible_creds,
):
    """ Test ansible custom button for with specific inventory execution

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        setup:
            1. Setup Target Machine with pingable hostname
            2. Create catalog with ansible catalog item
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with specific inventory
               (localhost/ Target Machine/ Specific Host)
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog with proper credentials and hostname
            7. Check for the proper flash message
            8. Check operation perform on target machine or not (here create test file).
    """
    group, obj_type = button_group

    if inventory == "Localhost":
        cred_name = "CFME Default Credential"
        hostname = appliance.hostname
        username = credentials["ssh"]["username"]
        password = credentials["ssh"]["password"]
    else:
        cred_name = target_machine_ansible_creds.name
        hostname = target_machine.hostname
        username = target_machine.username
        password = target_machine.password

    # Create button as per inventory
    button = group.buttons.create(
        type="Ansible Playbook",
        playbook_cat_item=ansible_catalog_item_create_empty_file.name,
        inventory=inventory,
        hosts=target_machine.hostname if inventory == "Specific Hosts" else None,
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(start="hover_"),
    )
    request.addfinalizer(button.delete_if_exists)

    # For target machine inventory target entity object is created target VM
    obj = target_machine.vm if inventory == "Target Machine" else setup_obj

    # Navigate to entity object and execute button
    view = navigate_to(obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(CredsHostsDialogView, wait="20s")
    dialog_view.fill({"machine_credential": cred_name})

    # Order playbook with custom button on host and validate file
    ansible_test_file = RemoteFile(hostname=hostname, username=username, password=password)

    with ansible_test_file.validate():
        dialog_view.submit.click()
        view.flash.assert_success_message("Order Request was Submitted")
