import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(2),
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

OBJ_TYPE_59 = ["PROVIDER", "CONTAINER_NODES", "CONTAINER_PROJECTS"]

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
