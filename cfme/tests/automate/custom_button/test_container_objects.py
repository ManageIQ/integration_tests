import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([ContainersProvider], selector=ONE_PER_TYPE),
]

CONTAINER_OBJECTS = [
    "CONTAINER_IMAGE",
    "CONTAINER_NODE",
    "CONTAINER_POD",
    "CONTAINER_PROJECT",
    "CONTAINER_TEMPLATE",
    "CONTAINER_VOLUME",
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
def setup_obj(appliance, button_group):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    if obj_type == "CONTAINER_IMAGE":
        obj = appliance.collections.container_images.all()[0]
    elif obj_type == "CONTAINER_NODE":
        obj = appliance.collections.container_nodes.all()[0]
    elif obj_type == "CONTAINER_POD":
        obj = appliance.collections.container_pods.all()[0]
    elif obj_type == "CONTAINER_PROJECT":
        obj = appliance.collections.container_projects.all()[0]
    elif obj_type == "CONTAINER_TEMPLATE":
        obj = appliance.collections.container_templates.all()[0]
    elif obj_type == "CONTAINER_VOLUME":
        obj = appliance.collections.container_volumes.all()[0]
    else:
        logger.error("No object collected for custom button object type '{}'".format(obj_type))
    return obj


@pytest.mark.ignore_stream('5.9')
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(request, display, setup_obj, button_group, provider):
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
