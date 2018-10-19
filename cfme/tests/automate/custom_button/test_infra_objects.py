import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]

INFRA_OBJECTS = ["PROVIDER", "HOST", "VM_INSTANCE", "TEMPLATE_IMAGE", "DATASTORE", "CLUSTER"]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]


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

    if obj_type == "PROVIDER":
        obj = provider
    elif obj_type == "HOST":
        obj = provider.appliance.collections.hosts.all()[0]
    elif obj_type == "VM_INSTANCE":
        obj = provider.appliance.provider_based_collection(provider).all()[0]
    elif obj_type == "TEMPLATE_IMAGE":
        obj = provider.appliance.collections.infra_templates.all()[0]
    elif obj_type == "DATASTORE":
        obj = provider.appliance.collections.datastores.filter({"provider": provider}).all()[0]
    elif obj_type == "CLUSTER":
        obj = provider.appliance.collections.clusters.all()[0]
    else:
        logger.error("No object collected for custom button object type '{}'".format(obj_type))
    return obj


@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(request, display, setup_obj, button_group):
    """ Test custom button display on a targeted page

    prerequisites:
        * Appliance with Infra provider

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

        # Note: For VM, custom button not display on All page but only VM page.
        if obj_type == "VM_INSTANCE" and destination == "All":
            destination = "VMsOnly"

        # Note: For VM Template, custom button not display on All page but only TemplatesOnly.
        if obj_type == "TEMPLATE_IMAGE" and destination == "All":
            destination = "TemplatesOnly"

        view = navigate_to(obj, destination)
        custom_button_group = Dropdown(view, group.hover)
        assert custom_button_group.is_displayed
        assert custom_button_group.has_item(button.text)


@pytest.mark.parametrize(
    "submit", SUBMIT, ids=["_".join(item.split()) for item in SUBMIT]
)
@pytest.mark.meta(
    blockers=[
        BZ(1628224, forced_streams=["5.10"], unblock=lambda submit: submit != "Submit all")
    ]
)
def test_custom_button_automate(appliance, request, submit, setup_obj, button_group):
    """ Test custom button for automate and requests count as per submit

    prerequisites:
        * Appliance with Infra provider

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

        # Note: For VM, custom button not display on `All page` but only `VM page`.
        if obj_type == "VM_INSTANCE" and destination == "All":
            destination = "VMsOnly"

        # Note: For VM Template, custom button not display on All page but only TemplatesOnly.
        if obj_type == "TEMPLATE_IMAGE" and destination == "All":
            destination = "TemplatesOnly"

        view = navigate_to(obj, destination)
        custom_button_group = Dropdown(view, group.hover)
        assert custom_button_group.has_item(button.text)

        # Entity count depends on the destination for `All` available entities and
        # `Details` means a single entity.
        if destination in ["All", "VMsOnly", "TemplatesOnly"]:
            try:
                paginator = view.paginator
            except AttributeError:
                paginator = view.entities.paginator

            entity_count = min(paginator.items_amount, paginator.items_per_page)
            paginator.check_all()
        else:
            entity_count = 1

        # Clear the automation log
        assert appliance.ssh_client.run_command('echo -n "" > /var/www/miq/vmdb/log/automation.log')

        custom_button_group.item_select(button.text)
        view.flash.assert_message('"{}" was executed'.format(button.text))

        # Submit all: single request for all entity execution
        # One by one: separate requests for all entity execution
        expected_count = 1 if submit == "Submit all" else entity_count
        try:
            wait_for(
                log_request_check,
                [appliance, expected_count],
                timeout=600,
                message="Check for expected request count",
                delay=20,
            )
        except TimedOutError:
            assert False, "Expected {} requests not found in automation log".format(
                str(expected_count)
            )
