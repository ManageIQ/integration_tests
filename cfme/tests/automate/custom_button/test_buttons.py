# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [
    test_requirements.automate,
    pytest.mark.usefixtures('uses_infra_providers'),
]


OBJ_TYPE_59 = [
    "CLOUD_TENANT",
    "CLOUD_VOLUME",
    "CLUSTER",
    "CONTAINER_NODES",
    "CONTAINER_PROJECTS",
    "DATASTORE",
    "GENERIC",
    "HOST",
    "PROVIDER",
    "SERVICE",
    "TEMPLATE_IMAGE",
    "VM_INSTANCE",
]

OBJ_TYPE = [
    "AZONE",
    "CLOUD_NETWORK",
    "CLOUD_OBJECT_STORE_CONTAINER",
    "CLOUD_SUBNET",
    "CLOUD_TENANT",
    "CLOUD_VOLUME",
    "CLUSTER",
    "CONTAINER_IMAGES",
    "CONTAINER_NODES",
    "CONTAINER_PODS",
    "CONTAINER_PROJECTS",
    "CONTAINER_TEMPLATES",
    "CONTAINER_VOLUMES",
    "DATASTORE",
    "GROUP",
    "USER",
    "GENERIC",
    "HOST",
    "LOAD_BALANCER",
    "ROUTER",
    "ORCHESTRATION_STACK",
    "PROVIDER",
    "SECURITY_GROUP",
    "SERVICE",
    "SWITCH",
    "TENANT",
    "TEMPLATE_IMAGE",
    "VM_INSTANCE",
]


@pytest.fixture(scope="module")
def buttongroup(appliance):
    def _buttongroup(object_type):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            type=getattr(collection, object_type)
        )
        return button_gp
    return _buttongroup


# IMPORTANT: This is a canonical test. It shows how a proper test should look like under new order.
@pytest.mark.sauce
@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_button_group_crud(request, appliance, obj_type):
    """Test Creating a Button Group

    Prerequisities:
        * An appliance

    Steps:
        * Create a Button Group with random button text and button hover text, select type Service
        * Assert that the button group exists
        * Assert that the entered values correspond with what is displayed on the details page
        * Change the hover text, ensure the text is changed on details page
        * Delete the button group
        * Assert that the button group no longer exists.
    """
    # 1) Create it
    collection = appliance.collections.button_groups
    buttongroup = collection.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=getattr(collection, obj_type, None),
    )

    # Ensure it gets deleted after the test
    request.addfinalizer(buttongroup.delete_if_exists)
    # 2) Verify it exists
    assert buttongroup.exists
    # 3) Now the new part, go to the details page
    view = navigate_to(buttongroup, 'Details')
    # 4) and verify that the values in there indeed correspond to the values specified
    assert view.text.text == buttongroup.text
    assert view.hover.text == buttongroup.hover
    # 5) generate a random string for update test
    updated_hover = "edit_desc_{}".format(fauxfactory.gen_alphanumeric())
    # 6) Update it (this might go over multiple fields in the object)
    with update(buttongroup):
        buttongroup.hover = updated_hover
    # 7) Assert it still exists
    assert buttongroup.exists
    # 8) Go to the details page again
    view = navigate_to(buttongroup, 'Details')
    # 9) Verify it indeed equals to what it was set to before
    assert view.hover.text == updated_hover
    # 10) Delete it - first cancel and then real
    buttongroup.delete(cancel=True)
    assert buttongroup.exists
    buttongroup.delete()
    # 11) Verify it is deleted
    assert not buttongroup.exists


@pytest.mark.sauce
@pytest.mark.tier(2)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_button_crud(appliance, dialog, request, buttongroup, obj_type):
    """Test Creating a Button

    Prerequisities:
        * An Button Group

    Steps:
        * Create a Button with random button text and button hover text, and random request
        * Assert that the button exists
        * Assert that the entered values correspond with what is displayed on the details page
        * Change the hover text, ensure the text is changed on details page
        * Delete the button
        * Assert that the button no longer exists.

    Bugzillas:
        * 1143019, 1205235
    """
    button_gp = buttongroup(obj_type)
    button = button_gp.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.text.text == button.text
    assert view.hover.text == button.hover
    edited_hover = "edited {}".format(fauxfactory.gen_alphanumeric())
    with update(button):
        button.hover = edited_hover
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.hover.text == edited_hover
    button.delete(cancel=True)
    assert button.exists
    button.delete()
    assert not button.exists


@pytest.mark.meta(blockers=[BZ(1460774, forced_streams=["5.8", "upstream"])])
@pytest.mark.tier(2)
def test_button_avp_displayed(appliance, dialog, request):
    """This test checks whether the Attribute/Values pairs are displayed in the dialog.
       automates 1229348
    Steps:
        * Open a dialog to create a button.
        * Locate the section with attribute/value pairs.
    """
    # This is optional, our nav tree does not have unassigned button
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=appliance.collections.button_groups.VM_INSTANCE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttons_collection = appliance.collections.buttons
    buttons_collection.group = buttongroup
    view = navigate_to(buttons_collection, 'Add')
    for n in range(1, 6):
        assert view.advanced.attribute(n).key.is_displayed
        assert view.advanced.attribute(n).value.is_displayed
    view.cancel_button.click()


@pytest.mark.tier(3)
@pytest.mark.parametrize("field", ["icon", "request"])
def test_button_required(appliance, field):
    """Test Icon and Request are required field while adding custom button.

    Prerequisities:
        * Button Group

    Steps:
        * Try to add custom button without icon/request
        * Assert flash message.
    """
    unassigned_gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned Buttons", type="Provider"
    )
    button_coll = appliance.collections.buttons
    button_coll.group = unassigned_gp  # Need for supporting navigation

    view = navigate_to(button_coll, "Add")
    view.fill(
        {
            "options": {
                "text": fauxfactory.gen_alphanumeric(),
                "hover": fauxfactory.gen_alphanumeric(),
                "open_url": True,
            },
            "advanced": {"system": "Request", "request": "InspectMe"},
        }
    )

    if field == "icon":
        msg = "Button Icon must be selected"
    elif field == "request":
        view.fill({"options": {"image": "fa-user"}, "advanced": {"request": ""}})
        msg = "Request is required"

    view.title.click()  # Workaround automation unable to read upside flash message

    view.add_button.click()
    view.flash.assert_message(msg)
    view.cancel_button.click()
