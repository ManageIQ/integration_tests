# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.base.ui import AutomateSimulationView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import (
    log_request_check,
    OBJ_TYPE,
    OBJ_TYPE_59,
    TextInputDialogView,
)
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError, wait_for

pytestmark = [test_requirements.automate, pytest.mark.usefixtures("uses_infra_providers")]


@pytest.fixture(scope="module")
def buttongroup(appliance):
    def _buttongroup(object_type):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            type=getattr(collection, object_type),
        )
        return button_gp

    return _buttongroup


# IMPORTANT: This is a canonical test. It shows how a proper test should look like under new order.
@pytest.mark.sauce
@pytest.mark.tier(1)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_button_group_crud(request, appliance, obj_type):
    """Test crud operation for Button Group

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create a Button Group with random button text and hover, select type Service
            2. Assert that the button group exists
            3. Assert that the entered values correspond with what is displayed on the details page
            4. Change the hover text, ensure the text is changed on details page
            5. Delete the button group
            6. Assert that the button group no longer exists.
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
    view = navigate_to(buttongroup, "Details")
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
    view = navigate_to(buttongroup, "Details")
    # 9) Verify it indeed equals to what it was set to before
    assert view.hover.text == updated_hover
    # 10) Delete it - first cancel and then real
    buttongroup.delete(cancel=True)
    assert buttongroup.exists
    buttongroup.delete()
    # 11) Verify it is deleted
    assert not buttongroup.exists


@pytest.mark.sauce
@pytest.mark.tier(1)
@pytest.mark.uncollectif(
    lambda appliance, obj_type: obj_type not in OBJ_TYPE_59 and appliance.version < "5.10"
)
@pytest.mark.parametrize("obj_type", OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE])
def test_button_crud(appliance, dialog, request, buttongroup, obj_type):
    """Test crud operation for Custom Button

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create a Button with random button text and button hover text, and random request
            2. Assert that the button exists
            3. Assert that the entered values correspond with what is displayed on the details page
            4. Change the hover text, ensure the text is changed on details page
            5. Delete the button
            6. Assert that the button no longer exists.

    Bugzilla:
        1143019, 1205235
    """
    button_gp = buttongroup(obj_type)
    button = button_gp.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        dialog=dialog,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)
    assert button.exists
    view = navigate_to(button, "Details")
    assert view.text.text == button.text
    assert view.hover.text == button.hover
    edited_hover = "edited {}".format(fauxfactory.gen_alphanumeric())
    with update(button):
        button.hover = edited_hover
    assert button.exists
    view = navigate_to(button, "Details")
    assert view.hover.text == edited_hover
    button.delete(cancel=True)
    assert button.exists
    button.delete()
    assert not button.exists


@pytest.mark.tier(2)
def test_button_avp_displayed(appliance, dialog, request):
    """This test checks whether the Attribute/Values pairs are displayed in the dialog.

    Polarion:
        assignee: anikifor
        initialEstimate: 1/12h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Open a dialog to create a button.
            2. Locate the section with attribute/value pairs.

    Bugzilla:
        1229348, 1460774
    """
    # This is optional, our nav tree does not have unassigned button
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=appliance.collections.button_groups.VM_INSTANCE,
    )
    request.addfinalizer(buttongroup.delete_if_exists)
    buttons_collection = appliance.collections.buttons
    buttons_collection.group = buttongroup
    view = navigate_to(buttons_collection, "Add")
    for n in range(1, 6):
        assert view.advanced.attribute(n).key.is_displayed
        assert view.advanced.attribute(n).value.is_displayed
    view.cancel_button.click()


@pytest.mark.tier(3)
@pytest.mark.parametrize("field", ["icon", "request"])
def test_button_required(appliance, field):
    """Test Icon and Request are required field while adding custom button.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: low
        caseposneg: positive
        testtype: nonfunctional
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        setup: Button Group
        testSteps:
            1. Try to add custom button without icon/request
            2. Assert flash message.
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


@pytest.mark.tier(3)
def test_open_url_availability(appliance):
    """Test open URL option should only available for Single display.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: low
        caseposneg: positive
        testtype: nonfunctional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        setup: Button Group
        testSteps:
            1. Create a Button with other than Single display options
            2. Assert flash message.
    """

    unassigned_gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type="Provider"
    )
    button_coll = appliance.collections.buttons
    button_coll.group = unassigned_gp  # Need for supporting navigation

    view = navigate_to(button_coll, "Add")
    view.fill(
        {
            "options": {
                "text": "test_open_url",
                "hover": "Open Url Test",
                "image": "fa-user",
                "open_url": True,
            },
            "advanced": {"system": "Request", "request": "InspectMe"},
        }
    )

    for display in ["List", "Single and list"]:
        view.options.display_for.fill(display)
        view.add_button.click()
        view.flash.assert_message("URL can be opened only by buttons for a single entity")
    view.cancel_button.click()


@pytest.mark.provider([VMwareProvider], override=True, scope="function", selector=ONE_PER_TYPE)
@pytest.mark.uncollectif(
    lambda appliance: appliance.version < "5.10",
    reason="BZ-1646905 still not backported to lower version",
)
def test_custom_button_quotes(appliance, provider, setup_provider, dialog, request):
    """ Test custom button and group allows quotes or not

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: nonfunctional
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        setup: Simple TextInput service dialog
        testSteps:
            1. Create custom button group with single quote in name like "Group's"
            2. Create a custom button with quote in name like "button's"
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog and submit Check for the flash message related to button execution

    Bugzilla:
        1646905
    """
    # ToDo: collect test for 5.9; If developer backport BZ-1646905
    collection = appliance.collections.button_groups
    group = collection.create(
        text="Group's", hover="Group's Hover", type=getattr(collection, "PROVIDER")
    )
    request.addfinalizer(group.delete_if_exists)

    button = group.buttons.create(
        text="Button's",
        hover="Button's Hover",
        dialog=dialog,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    view = navigate_to(provider, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(TextInputDialogView, wait="60s")
    dialog_view.service_name.fill("Custom Button Execute")

    dialog_view.submit.click()
    view.flash.assert_message("Order Request was Submitted")


@pytest.mark.tier(2)
@pytest.mark.meta(
    blockers=[BZ(1535215, forced_streams=["5.10"], unblock=lambda button_tag: button_tag != "Evm")]
)
@pytest.mark.uncollectif(
    lambda appliance, button_tag: appliance.version < "5.10" and button_tag == "Evm",
    reason="for lower version evm custom button object not supported",
)
@pytest.mark.provider([VMwareProvider], override=True, scope="function", selector=ONE_PER_TYPE)
@pytest.mark.parametrize("button_tag", ["Evm", "Build"])
def test_custom_button_simulation(request, appliance, provider, setup_provider, button_tag):
    """ Test whether custom button works with simulation option

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button

    Bugzilla:
        1535215
    """
    if button_tag == "Evm":
        btn_type = "User"
        obj = appliance.collections.users.instantiate(name="Administrator")
    else:
        btn_type = "Provider"
        obj = provider

    gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type=btn_type
    )

    button = gp.buttons.create(
        text="Btn_{}".format(fauxfactory.gen_alphanumeric(2)),
        hover="Hover_{}".format(fauxfactory.gen_alphanumeric(2)),
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    # Clear the automation log
    assert appliance.ssh_client.run_command('echo -n "" > /var/www/miq/vmdb/log/automation.log')

    # Simulate button
    button.simulate(target_object=obj.name, instance=button.system, request=button.request)
    view = appliance.browser.create_view(AutomateSimulationView)
    view.flash.assert_message("Automation Simulation has been run")

    # Check in evm log
    try:
        wait_for(
            log_request_check,
            [appliance, 1],
            timeout=600,
            message="Check for expected request count",
            delay=20,
        )
    except TimedOutError:
        assert False, "Requests not found in automation log"


@pytest.mark.manual
@pytest.mark.tier(3)
def test_custom_button_language():
    """ There was bug with usecase before... (#1568417)

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. set the language to french
            2. go to automation-> automate -> customization
            3. check the custom buttons tree should not empty from automation

    Bugzilla:
        1568417
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_attribute_override():
    """ Test custom button attribute override

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: nonfunctional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. create a custom button to request the call_instance_with_message
            2. set the message to create
            3. set the attributes instance, class, namespace to "whatever"
            4. set the attribute message to "my_message"
            5. save it

    Bugzilla:
        1651099
    """
    pass
