from collections import namedtuple

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.ansible import RemoteFile
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import CredsHostsDialogView
from cfme.utils.appliance.implementations.ui import navigate_to


from cfme.utils.conf import credentials

pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
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

# "Target Machine"
# "Specific Hosts"
INVENTORY = ["Localhost"]
HostInfo = namedtuple("HostInfo", ["hostname", "username", "password", "cred_name"])


@pytest.fixture(
    params=INFRA_OBJECTS, ids=[obj.capitalize() for obj in INFRA_OBJECTS], scope="module"
)
def button_group(appliance, request):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=getattr(collection, request.param),
    )
    yield button_gp, request.param
    button_gp.delete_if_exists()


@pytest.fixture()
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
        pytest.skip("Object not found for {obj} type".format(obj=obj_type))

    return obj


@pytest.fixture(scope="module")
def ansible_creds(appliance):
    username = "root"
    password = "foo"
    creds = appliance.collections.ansible_credentials.create(
        name=fauxfactory.gen_alpha(start="cred_"),
        credential_type="Machine",
        username=username,
        password=password,
    )
    yield creds
    creds.delete_if_exists()


@pytest.fixture(params=INVENTORY, scope="module")
def host_credentials(request, appliance, ansible_creds):
    if request.param == "Localhost":
        hostname = appliance.hostname
        username = credentials["ssh"]["username"]
        password = credentials["ssh"]["password"]
        cred_name = "CFME Default Credential"
    else:
        hostname = "x.x.x.x"
        username = ansible_creds.username
        password = ansible_creds.password
        cred_name = ansible_creds.name

    return HostInfo(hostname, username, password, cred_name), request.param


def test_custom_button_automate_infra_obj_ansible(
    appliance,
    request,
    setup_obj,
    button_group,
    ansible_catalog_item_create_empty_file,
    host_credentials,
):
    """ Test ansible custom button for on localhost and specific host

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with specific inventory (localhost/ Specific Host)
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog with proper credentials and hostname
            7. Check for the proper flash message
            8. Check operation perform on host or not (here file create).
    """
    group, obj_type = button_group
    host, inventory = host_credentials

    # create button as per inventory
    button = group.buttons.create(
        type="Ansible Playbook",
        playbook_cat_item=ansible_catalog_item_create_empty_file.name,
        inventory=inventory,
        hosts=None if inventory == "Localhost" else host.hostname,
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(start="hover_"),
    )
    request.addfinalizer(button.delete_if_exists)

    # Navigate to entity object and execute button
    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(CredsHostsDialogView, wait="20s")
    dialog_view.fill(
        {
            "machine_credential": host.cred_name,
            "hosts": inventory.lower() if inventory == "Localhost" else host.hostname,
        }
    )

    # order playbook with custom button on host and valided file
    ansible_test_file = RemoteFile(
        hostname=host.hostname, username=host.username, password=host.password
    )

    with ansible_test_file.validate():
        dialog_view.submit.click()
        view.flash.assert_success_message("Order Request was Submitted")
