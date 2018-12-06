import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check, OBJ_TYPE_59, TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([ContainersProvider], selector=ONE_PER_TYPE),
    pytest.mark.meta(blockers=[BZ(1640304, forced_streams=["5.10"])]),
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


@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(request, display, setup_obj, button_group):
    """ Test custom button display on a targeted page

    prerequisites:
        * Appliance with Container provider

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with specific display
        * Navigate to object type page as per display selected
        * Single entity: Details page of the entity
        * List: All page of the entity
        * Single and list: Both All and Details page of the entity
        * Check for button group and button

    Polarion:
        assignee: ndhandre
        caseimportance: critical
        initialEstimate: 1/4h
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


@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
def test_custom_button_dialog(appliance, dialog, request, setup_obj, button_group):
    """ Test custom button with dialog and InspectMe method

    Prerequisites:
        * Appliance
        * Simple TextInput service dialog

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with service dialog
        * Navigate to object Details page
        * Check for button group and button
        * Select/execute button from group dropdown for selected entities
        * Fill dialog and submit
        * Check for the proper flash message related to button execution
        * Check request in automation log

    Polarion:
        assignee: None
        initialEstimate: None
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

    dialog_view = view.browser.create_view(TextInputDialogView)
    dialog_view.wait_displayed()
    assert dialog_view.service_name.fill("Custom Button Execute")

    # Clear the automation log
    assert appliance.ssh_client.run_command('echo -n "" > /var/www/miq/vmdb/log/automation.log')

    # Submit order
    dialog_view.submit.click()
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


@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression(appliance, request, setup_obj, button_group, expression):
    """ Test custom button as per expression enablement/visibility.
    prerequisites:
        * Appliance with Infra provider
    Steps:
        * Create custom button group with the Object type
        * Create a custom button with expression (Tag)
            1. Enablement Expression
            2. Visibility Expression
        * Navigate to object Detail page
        * Check: button should not enable/visible without tag
        * Check: button should enable/visible with tag

    Polarion:
        assignee: None
        initialEstimate: None
    """

    group, obj_type = button_group
    exp = {expression: {"tag": "My Company Tags : Department", "value": "Engineering"}}
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
    custom_button_group = Dropdown(view, group.hover)

    if tag.display_name in [item.display_name for item in setup_obj.get_tags()]:
        if expression == "enablement":
            assert custom_button_group.item_enabled(button.text)
            setup_obj.remove_tag(tag)
            if appliance.version < "5.10":
                assert not custom_button_group.item_enabled(button.text)
            else:
                assert not custom_button_group.is_enabled
        elif expression == "visibility":
            assert custom_button_group.is_displayed
            setup_obj.remove_tag(tag)
            assert not custom_button_group.is_displayed
    else:
        if expression == "enablement":
            if appliance.version < "5.10":
                assert not custom_button_group.item_enabled(button.text)
            else:
                assert not custom_button_group.is_enabled
            setup_obj.add_tag(tag)
            assert custom_button_group.item_enabled(button.text)
        elif expression == "visibility":
            assert not custom_button_group.is_displayed
            setup_obj.add_tag(tag)
            assert custom_button_group.is_displayed
