# -*- coding: utf-8 -*-
import random

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.base.ui import AutomateSimulationView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check
from cfme.tests.automate.custom_button import OBJ_TYPE
from cfme.tests.automate.custom_button import OBJ_TYPE_59
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.custom_button, pytest.mark.usefixtures("uses_infra_providers")]


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


@pytest.fixture(params=OBJ_TYPE, ids=[obj.capitalize() for obj in OBJ_TYPE], scope="module")
def button_group(appliance, request):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(start="hover_"),
        type=getattr(collection, request.param),
    )
    yield button_gp, request.param
    button_gp.delete_if_exists()


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
        1143019
        1205235
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
        assignee: ndhandre
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
        1229348
        1460774
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
        text="[Unassigned Buttons]", hover="Unassigned Buttons", type="VM and Instance"
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

    Bugzilla:
        1706900
    """

    unassigned_gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type="VM and Instance"
    )
    button_coll = appliance.collections.buttons
    button_coll.group = unassigned_gp  # Need for supporting navigation

    view = navigate_to(button_coll, "Add")

    # check for VM and Instance open url option enable for single display
    assert view.options.open_url.is_enabled

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

    # check open url facility other than single display.
    for display in ["List", "Single and list"]:
        view.options.display_for.fill(display)
        if appliance.version < "5.11":
            # less than 5.11; we have flash message for display checks
            view.add_button.click()
            view.flash.assert_message("URL can be opened only by buttons for a single entity")
        else:
            # from 5.11; for other than single checkbox will disabled
            assert not view.options.open_url.is_enabled

    view.cancel_button.click()


@pytest.mark.provider([VMwareProvider], override=True, scope="function", selector=ONE_PER_TYPE)
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
@pytest.mark.provider([VMwareProvider], override=True, scope="function", selector=ONE_PER_TYPE)
@pytest.mark.parametrize("button_tag", ["Evm", "Build"])
def test_custom_button_simulation(request, appliance, provider, setup_provider, button_tag):
    """ Test whether custom button works with simulation option
    Note: For version less than 5.10 EVM custom button object not supported.

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


@pytest.mark.uncollectif(
    lambda appliance, button_tag: appliance.version < "5.10" and button_tag == "Evm",
    reason="Evm objects not available in lower version",
)
@pytest.mark.parametrize("button_tag", ["Evm", "Build"])
@pytest.mark.provider([VMwareProvider], override=True, scope="module", selector=ONE_PER_TYPE)
def test_custom_button_order_sort(appliance, request, provider, setup_provider, button_tag):
    """ Test custom button order reflection on destination
    # ToDo: Now, we are testing this against single object per group tag. If need extends for all.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create [Unassigned Buttons] custom buttons
            2. Create custom button Group with unassigned buttons
            3. Navigate to object Details page
            4. Check for custom button order
            5. Update order of custom buttons
            6. Navigate to object Details page
            7. Check for custom button order updated or not
    Bugzilla:
        1628737
    """
    if button_tag == "Evm":
        btn_type = "Group"
        obj = appliance.collections.groups.instantiate(description="EvmGroup-super_administrator")
    else:
        btn_type = "Provider"
        obj = provider

    unassigned_gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type=btn_type
    )

    buttons = []
    for ind in range(0, 4):
        button = unassigned_gp.buttons.create(
            text="button_{n}_{f}".format(n=str(ind), f=fauxfactory.gen_alphanumeric(2)),
            hover="hover_{n}_{f}".format(n=str(ind), f=fauxfactory.gen_alphanumeric(2)),
            system="Request",
            request="InspectMe",
        )
        buttons.append(button)

    @request.addfinalizer
    def _clean():
        for btn in buttons:
            btn.delete_if_exists()

    unassigned_buttons = [btn.text for btn in buttons]

    group = appliance.collections.button_groups.create(
        text="group_{}".format(fauxfactory.gen_alphanumeric(3)),
        hover="hover_{}".format(fauxfactory.gen_alphanumeric(3)),
        type=btn_type,
        assign_buttons=unassigned_buttons,
    )
    request.addfinalizer(group.delete_if_exists)

    view = navigate_to(obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.items == unassigned_buttons

    # shuffle order of buttons
    shuffle_buttons = list(unassigned_buttons)
    random.shuffle(shuffle_buttons, random.random)

    with update(group):
        group.assign_buttons = shuffle_buttons
    navigate_to(obj, "Details")
    assert custom_button_group.items == shuffle_buttons


@pytest.mark.tier(3)
def test_custom_button_role_selection(appliance, request):
    """Test custom button role selection

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: medium
        startsin: 5.8
        casecomponent: CustomButton
        testSteps:
            1. Add custom button with specific roles and verify from summary page
            2. Update roles and verify
            3. Update button for role access to All and verify

    Bugzilla:
        1703588
    """
    test_roles = ["EvmRole-administrator", "EvmRole-security"]

    unassigned_gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned Buttons", type="Provider"
    )
    btn = unassigned_gp.buttons.create(
        text="group_{}".format(fauxfactory.gen_alphanumeric(3)),
        hover="hover_{}".format(fauxfactory.gen_alphanumeric(3)),
        system="Request",
        request="InspectMe",
        roles=test_roles,
    )
    request.addfinalizer(btn.delete_if_exists)

    assert btn.user_roles == test_roles

    test_roles.append("EvmRole-user_self_service")
    btn.update({"roles": test_roles})
    assert btn.user_roles == test_roles

    btn.update({"role_show": "<To All>"})
    assert btn.user_roles == "To All"


@pytest.mark.manual("manualonly")
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
        expectedResults:
            1.
            2. Navigate as per french i18n code
            3. check we are getting french i18n code in tree

    Bugzilla:
        1568417
    """
    pass


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1651099])
@pytest.mark.provider([VMwareProvider], override=True, selector=ONE_PER_TYPE)
def test_attribute_override(appliance, request, provider, setup_provider, buttongroup):
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
    attributes = [
        ("class", "Request"),
        ("instance", "TestNotification"),
        ("message", "digitronik_msg"),
        ("namespace", "/System"),
    ]
    req = "call_instance_with_message"
    patterns = [
        "[miqaedb:/System/Request/TestNotification#create]",
        "[miqaedb:/System/Request/TestNotification#digitronik_msg]"
    ]

    group = buttongroup("PROVIDER")
    button = group.buttons.create(
        text="btn_{}".format(fauxfactory.gen_alphanumeric(3)),
        hover="hover_{}".format(fauxfactory.gen_alphanumeric(3)),
        system="Request",
        request=req,
        attributes=attributes,
    )
    request.addfinalizer(button.delete_if_exists)

    # Initialize Log Checks
    log = LogValidator("/var/www/miq/vmdb/log/automation.log", matched_patterns=patterns)
    log.start_monitoring()

    # Execute button
    view = navigate_to(provider, "Details")
    custom_button_group = Dropdown(view, group.hover)
    custom_button_group.item_select(button.text)

    # Simulate button
    button.simulate(provider.name, request=req)

    # validate log requests for simulation and actual execution
    log.validate(wait="120s")


@pytest.mark.meta(blockers=[BZ(1719282, unblock=lambda button_type: button_type != "User")])
@pytest.mark.parametrize("button_type", ["User", "Provider"])
@pytest.mark.provider([VMwareProvider], override=True, scope="module", selector=ONE_PER_TYPE)
def test_simulated_object_copy_on_button(appliance, provider, setup_provider, button_type):
    """ Test copy of simulated object over custom button

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. simulate button with Automate -> Simulation
            2. copy simulated data
            3. paste simulated data on button from Automate -> Customizationn -> Buttons
            4. check copy-paste working or not

    Bugzilla:
        1426390
        1719282
    """
    if button_type == "User":
        target_type = "{}User".format("EVM " if appliance.version < "5.11" else "")
        target_obj = "Administrator"
    else:
        target_type = "Provider"
        target_obj = provider.name

    attributes = {
        "class": "Request",
        "instance": "TestNotification",
        "message": "digitronik_msg",
        "namespace": "/System",
    }

    # simulate and copy
    simulate(
        appliance=appliance,
        instance="Automation",
        message="test_bz",
        request="InspectMe",
        target_type=target_type,
        target_object=target_obj,
        execute_methods=True,
        pre_clear=True,
        attributes_values=attributes
    )

    view = appliance.browser.create_view(AutomateSimulationView, wait="15s")
    view.copy.click()

    # paste data while creating button
    button_coll = appliance.collections.buttons
    button_coll.group = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type=button_type
    )

    view = navigate_to(button_coll, "Add")
    view.paste.click()

    # check paste attributes
    assert view.advanced.system.read() == "Automation"
    assert view.advanced.message.read() == "test_bz"
    assert view.advanced.request.read() == "InspectMe"

    attributes_on_page = [kv for kv in view.advanced.attribute.read().values() if kv["key"] != ""]

    for attr in attributes_on_page:
        assert attributes[attr["key"]] == attr["value"]


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1755229)], automates=[1755229])
def test_under_group_multiple_button_crud(appliance, button_group, dialog):
    """Test multiple button creation and deletion under same group

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/10h
        caseimportance: critical
        startsin: 5.8
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create a Button Group
            2. Create button and delete button
            3. Repeat step-2 multiple time
    """
    button_gp, obj_type = button_group
    view = navigate_to(button_gp, "Details")

    for exp in ["enablement", "visibility"]:
        expression = {exp: {"tag": "My Company Tags : Department", "value": "Engineering"}}

        button = button_gp.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(start="hover_"),
            dialog=dialog,
            system="Request",
            request="InspectMe",
            **expression
        )
        view.flash.assert_message(f'Custom Button "{button.hover}" was added')
        assert button.exists
        button.delete()
        view.flash.assert_message(f'Button "{button.hover}": Delete successful')
        assert not button.exists
        button_gp.exists
