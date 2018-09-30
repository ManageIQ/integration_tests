import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.tests.automate.custom_button import check_log_requests_count, log_request_check
from cfme.utils.appliance.implementations.ui import navigate_to
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


@pytest.mark.uncollectif(lambda appliance: appliance.version < "5.10")
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


@pytest.mark.uncollectif(lambda appliance: appliance.version < "5.10")
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
        * 1628224
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
            entity_count = view.paginator.items_amount  # we are counting entity on same page
            view.paginator.check_all()
        else:
            entity_count = 1

        # First collect number of request already available in automation log
        initial_request_count = check_log_requests_count(appliance)
        custom_button_group.item_select(button.text)
        view.flash.assert_message('"{}" was executed'.format(button.text))

        # Submit all: single request for all entity execution
        # One by one: separate requests for all entity execution
        expected_count = 1 if submit == "Submit all" else entity_count
        try:
            wait_for(
                log_request_check,
                [appliance, initial_request_count, expected_count],
                timeout=120,
                message="Check for expected request count",
                delay=10,
            )
        except TimedOutError:
            assert False, "Expected {} requests not found in automation log".format(
                str(expected_count)
            )
