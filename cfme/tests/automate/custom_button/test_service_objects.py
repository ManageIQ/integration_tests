import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.services.myservice import MyService
from cfme.utils.appliance import ViaREST, ViaUI, ViaSSUI
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.blockers import BZ


pytestmark = [pytest.mark.tier(2)]

OBJECTS = ["SERVICE", "GENERIC"]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}


@pytest.fixture(scope="module")
def service(appliance):
    service_name = "service_{}".format(fauxfactory.gen_numeric_string(3))
    service = appliance.rest_api.collections.services.action.create(
        name=service_name, display=True
    )[0]
    yield service
    service.action.delete()


@pytest.fixture(scope="module")
def definition(appliance):
    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name="generic_class_{}".format(fauxfactory.gen_numeric_string(3)),
            description="Generic Object Definition",
            attributes={"addr01": "string"},
            associations={"services": "Service"},
            methods=["add_vm", "remove_vm"],
        )
        yield definition
        if definition.exists:
            definition.delete()


@pytest.fixture(scope="module")
def objects(appliance, definition, service):
    with appliance.context.use(ViaREST):
        instance = appliance.collections.generic_objects.create(
            name="generic_instance_{}".format(fauxfactory.gen_numeric_string(3)),
            definition=definition,
            attributes={"addr01": "Test Address"},
            associations={"services": [service]},
        )
        service.action.add_resource(
            resource=appliance.rest_api.collections.generic_objects.find_by(name=instance.name)[
                0
            ]._ref_repr()
        )
        instance.my_service = MyService(appliance, name=service.name)

        obj_dest = {
            "GENERIC": {
                "All": (instance.my_service, "GenericObjectInstance"),
                "Details": (instance, "MyServiceDetails"),
            },
            "SERVICE": {
                "All": (instance.my_service, "All"),
                "Details": (instance.my_service, "Details"),
            },
        }
        yield obj_dest
        if instance.exists:
            instance.delete()


@pytest.fixture(params=OBJECTS, ids=[obj.capitalize() for obj in OBJECTS], scope="module")
def button_group(appliance, request):
    with appliance.context.use(ViaUI):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            type=getattr(collection, request.param),
        )
        yield button_gp, request.param
        button_gp.delete_if_exists()


@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=[item.replace(" ", "_") for item in DISPLAY_NAV.keys()]
)
@pytest.mark.uncollectif(
    lambda context, button_group: context == ViaSSUI and "GENERIC" in button_group
)
@pytest.mark.meta(
    blockers=[
        BZ(
            1650066,
            forced_streams=["5.9", "5.10"],
            unblock=lambda display, context: not (
                context is ViaSSUI and display in ["List", "Single and list"]
            ),
        )
    ]
)
def test_custom_button_display(request, appliance, context, display, objects, button_group):
    """ Test custom button display on a targeted page

    prerequisites:
        * Appliance with Service and Generic object setup

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with specific display
        * Navigate to object type page as per display selected [For service SSUI]
        * Single entity: Details page of the entity
        * List: All page of the entity
        * Single and list: Both All and Details page of the entity
        * Check for button group and button

    Bugzilla:
        * 1650066
    """

    group, obj_type = button_group

    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            display_for=display,
            system="Request",
            request="InspectMe",
        )
        request.addfinalizer(button.delete_if_exists)

    with appliance.context.use(context):
        navigate_to = ssui_nav if context is ViaSSUI else ui_nav
        for destination in DISPLAY_NAV[display]:
            obj = objects[obj_type][destination][0]
            dest_name = objects[obj_type][destination][1]
            view = navigate_to(obj, dest_name)
            custom_button_group = Dropdown(view, group.text)
            assert custom_button_group.is_displayed
            assert custom_button_group.has_item(button.text)
