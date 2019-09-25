import re

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([ContainersProvider], selector=ONE_PER_TYPE),
]

CONTAINER_OBJECTS = [
    "PROVIDER",
    "CONTAINER_IMAGES",
    "CONTAINER_NODES",
    "CONTAINER_PODS",
    "CONTAINER_PROJECTS",
    "CONTAINER_TEMPLATES",
    "CONTAINER_VOLUMES",
]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}


@pytest.fixture(
    params=CONTAINER_OBJECTS, ids=[obj.capitalize() for obj in CONTAINER_OBJECTS], scope="module"
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
def setup_obj(appliance, provider, button_group):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    try:
        if obj_type == "PROVIDER":
            obj = provider
        else:
            obj = getattr(appliance.collections, obj_type.lower()).all()[0]
    except IndexError:
        pytest.skip("Object not found for {obj} type".format(obj=obj_type))

    if not obj.exists:
        pytest.skip("{obj} object not exist".format(obj=obj_type))
    return obj


@pytest.mark.tier(1)
@pytest.mark.parametrize(
    "display",
    list(DISPLAY_NAV.keys()),
    ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display_container_obj(request, display, setup_obj, button_group):
    """ Test custom button display on a targeted page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with specific display
            3. Navigate to object type page as per display selected
            4. Single entity: Details page of the entity
            5. List: All page of the entity
            6. Single and list: Both All and Details page of the entity
            7. Check for button group and button
    """

    group, obj_type = button_group
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        display_for=display,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    for destination in DISPLAY_NAV[display]:
        obj = setup_obj.parent if destination == "All" else setup_obj

        view = navigate_to(obj, destination)
        custom_button_group = Dropdown(view, group.hover)
        assert custom_button_group.is_displayed
        assert custom_button_group.has_item(button.text)


@pytest.mark.meta(automates=[1729903, 1732489])
def test_custom_button_dialog_container_obj(appliance, dialog, request, setup_obj, button_group):
    """ Test custom button with dialog and InspectMe method

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with service dialog
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog and submit
            7. Check for the proper flash message related to button execution
            8. Check request in automation log

    Bugzilla:
        1729903
        1732489
    """

    group, obj_type = button_group

    # Note: No need to set display_for dialog only work with Single entity
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        dialog=dialog,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(TextInputDialogView, wait="10s")
    assert dialog_view.service_name.fill("Custom Button Execute")

    # Clear the automation log
    assert appliance.ssh_client.run_command('echo -n "" > /var/www/miq/vmdb/log/automation.log')

    # Submit order
    dialog_view.submit.click()

    if not (BZ(1732489, forced_streams=["5.10", "5.11"]).blocks and obj_type == "PROVIDER"):
        view.flash.assert_message("Order Request was Submitted")

    # Check for request in automation log
    try:
        wait_for(
            log_request_check,
            [appliance, 1],
            timeout=300,
            message="Check for expected request count",
            delay=20,
        )
    except TimedOutError:
        assert False, "Expected 1 requests not found in automation log"


@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression_container_obj(
    appliance, request, setup_obj, button_group, expression
):
    """ Test custom button as per expression enablement/visibility.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with expression (Tag)
                a. Enablement Expression
                b. Visibility Expression
            3. Navigate to object Detail page
            4. Check: button should not enable/visible without tag
            5. Check: button should enable/visible with tag
    """

    group, obj_type = button_group
    exp = {expression: {"tag": "My Company Tags : Department", "value": "Engineering"}}
    disabled_txt = "Tag - My Company Tags : Department : Engineering"
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        display_for="Single entity",
        system="Request",
        request="InspectMe",
        **exp
    )
    request.addfinalizer(button.delete_if_exists)

    tag_cat = appliance.collections.categories.instantiate(
        name="department", display_name="Department"
    )
    tag = tag_cat.collections.tags.instantiate(name="engineering", display_name="Engineering")

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.text)

    if tag in setup_obj.get_tags():
        if expression == "enablement":
            assert custom_button_group.item_enabled(button.text)
            setup_obj.remove_tag(tag)
            assert not custom_button_group.is_enabled
            assert re.search(disabled_txt, custom_button_group.hover)
        elif expression == "visibility":
            assert button.text in custom_button_group.items
            setup_obj.remove_tag(tag)
            assert not custom_button_group.is_displayed
    else:
        if expression == "enablement":
            assert not custom_button_group.is_enabled
            assert re.search(disabled_txt, custom_button_group.hover)
            setup_obj.add_tag(tag)
            assert custom_button_group.item_enabled(button.text)
        elif expression == "visibility":
            assert not custom_button_group.is_displayed
            setup_obj.add_tag(tag)
            assert button.text in custom_button_group.items
