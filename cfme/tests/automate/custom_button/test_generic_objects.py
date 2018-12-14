import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.tests.automate.custom_button import log_request_check, TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [pytest.mark.tier(2)]


OBJECTS = ["USER", "GROUP", "TENANT"]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]


@pytest.fixture(params=OBJECTS, ids=[obj.capitalize() for obj in OBJECTS], scope="module")
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
def setup_obj(appliance, button_group):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    if obj_type == "USER":
        obj = appliance.collections.users.instantiate(name="Administrator")
    elif obj_type == "GROUP":
        obj = appliance.collections.groups.instantiate(description="EvmGroup-super_administrator")
    elif obj_type == "TENANT":
        obj = appliance.collections.tenants.get_root_tenant()
    else:
        logger.error("No object collected for custom button object type '{}'".format(obj_type))
    return obj


@pytest.mark.ignore_stream("5.9")
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(request, display, setup_obj, button_group):
    """ Test custom button display on a targeted page

    prerequisites:
        * Appliance

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


@pytest.mark.ignore_stream("5.9")
@pytest.mark.meta(
    blockers=[
        BZ(
            1642939,
            forced_streams=["5.10"],
            unblock=lambda button_group: "GROUP" not in button_group,
        )
    ]
)
@pytest.mark.parametrize("submit", SUBMIT, ids=["_".join(item.split()) for item in SUBMIT])
def test_custom_button_automate(appliance, request, submit, setup_obj, button_group):
    """ Test custom button for automate and requests count as per submit

    prerequisites:
        * Appliance

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with specific submit option and Single and list display
        * Navigate to object type pages (All and Details)
        * Check for button group and button
        * Select/execute button from group dropdown for selected entities
        * Check for the proper flash message related to button execution
        * Check automation log requests. Submitted as per selected submit option or not.
        * Submit all: single request for all entities execution
        * One by one: separate requests for all entities execution

    Bugzillas:
        * 1628224, 1642939

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
    """

    group, obj_type = button_group
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        display_for="Single and list",
        submit=submit,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    for destination in ["All", "Details"]:
        obj = setup_obj.parent if destination == "All" else setup_obj
        view = navigate_to(obj, destination)
        custom_button_group = Dropdown(view, group.hover)
        assert custom_button_group.has_item(button.text)

        # Entity count depends on the destination for `All` available entities and
        # `Details` means a single entity.
        if destination == "All":
            entity_count = min(view.paginator.items_amount, view.paginator.items_per_page)
            view.paginator.check_all()
        else:
            entity_count = 1

        # Clear the automation log
        assert appliance.ssh_client.run_command(
            'echo -n "" > /var/www/miq/vmdb/log/automation.log'
        )

        custom_button_group.item_select(button.text)
        view.flash.assert_message('"{}" was executed'.format(button.text))

        # Submit all: single request for all entity execution
        # One by one: separate requests for all entity execution
        expected_count = 1 if submit == "Submit all" else entity_count
        try:
            wait_for(
                log_request_check,
                [appliance, expected_count],
                timeout=120,
                message="Check for expected request count",
                delay=10,
            )
        except TimedOutError:
            assert False, "Expected {} requests not found in automation log".format(
                str(expected_count)
            )


@pytest.mark.ignore_stream("5.9")
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
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
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

    view.wait_displayed("60s")
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


@pytest.mark.ignore_stream("5.9")
@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression(appliance, request, setup_obj, button_group, expression):
    """ Test custom button as per expression enablement/visibility.

    prerequisites:
        * Appliance

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with expression (Tag)
            1. Enablement Expression
            2. Visibility Expression
        * Navigate to object Detail page
        * Check: button should not enable/visible without tag
        * Check: button should enable/visible with tag

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
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
            assert not custom_button_group.is_enabled
        elif expression == "visibility":
            assert custom_button_group.is_displayed
            setup_obj.remove_tag(tag)
            assert not custom_button_group.is_displayed
    else:
        if expression == "enablement":
            assert not custom_button_group.is_enabled
            setup_obj.add_tag(tag)
            assert custom_button_group.item_enabled(button.text)
        elif expression == "visibility":
            assert not custom_button_group.is_displayed
            setup_obj.add_tag(tag)
            assert custom_button_group.is_displayed
