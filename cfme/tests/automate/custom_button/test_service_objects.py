import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.services.myservice import MyService
from cfme.tests.automate.custom_button import CustomButtonSSUIDropdwon, log_request_check
from cfme.utils.appliance import ViaREST, ViaUI, ViaSSUI
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [pytest.mark.tier(2)]

OBJECTS = ["SERVICE", "GENERIC"]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]

TEXT_DISPLAY = {
    "group": {"group_display": False, "btn_display": True},
    "button": {"group_display": True, "btn_display": False},
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


@pytest.fixture(params=TEXT_DISPLAY, scope="module")
def serv_button_group(appliance, request):

    with appliance.context.use(ViaUI):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text="group_{}".format(fauxfactory.gen_numeric_string(3)),
            hover="hover_{}".format(fauxfactory.gen_alphanumeric(3)),
            display=TEXT_DISPLAY[request.param]["group_display"],
            type=getattr(collection, "SERVICE"),
        )

        button = button_gp.buttons.create(
            text="btn_{}".format(fauxfactory.gen_numeric_string(3)),
            hover="hover_{}".format(fauxfactory.gen_alphanumeric(3)),
            display=TEXT_DISPLAY[request.param]["btn_display"],
            display_for="Single and list",
            system="Request",
            request="InspectMe",
        )
        yield button, button_gp
        button_gp.delete_if_exists()
        button.delete_if_exists()


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

    Polarion:
        assignee: ndhandre
        caseimportance: critical
        initialEstimate: 1/4h
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


@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.parametrize("submit", SUBMIT, ids=[item.replace(" ", "_") for item in SUBMIT])
@pytest.mark.uncollectif(
    lambda context, button_group: context == ViaSSUI and "GENERIC" in button_group
)
def test_custom_button_automate(request, appliance, context, submit, objects, button_group):
    """ Test custom button for automate and requests count as per submit

    prerequisites:
        * Appliance with service and generic object

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
        * 1650066

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
    """

    group, obj_type = button_group
    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            display_for="Single and list",
            submit=submit,
            system="Request",
            request="InspectMe",
        )
        request.addfinalizer(button.delete_if_exists)

    with appliance.context.use(context):
        navigate_to = ssui_nav if context is ViaSSUI else ui_nav

        # BZ-1650066: no custom button on All page
        destinations = (
            ["Details"]
            if context == ViaSSUI and BZ(1650066, forced_streams=["5.9", "5.10"]).blocks
            else ["All", "Details"]
        )
        for destination in destinations:
            obj = objects[obj_type][destination][0]
            dest_name = objects[obj_type][destination][1]
            view = navigate_to(obj, dest_name)
            custom_button_group = Dropdown(view, group.text)
            assert custom_button_group.has_item(button.text)

            # Entity count depends on the destination for `All` available entities and
            # `Details` means a single entity.

            if destination == "All":
                try:
                    paginator = view.paginator
                except AttributeError:
                    paginator = view.entities.paginator

                entity_count = min(paginator.items_amount, paginator.items_per_page)
                view.entities.paginator.check_all()
            else:
                entity_count = 1

            # Clear the automation log
            assert appliance.ssh_client.run_command(
                'echo -n "" > /var/www/miq/vmdb/log/automation.log'
            )

            custom_button_group.item_select(button.text)

            # SSUI not support flash messages
            if context is ViaUI:
                view.flash.assert_message('"{button}" was executed'.format(button=button.text))

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
                assert False, "Expected {count} requests not found in automation log".format(
                    count=str(expected_count)
                )


@pytest.mark.meta(
    blockers=[
        BZ(
            1659452,
            forced_streams=["5.9", "5.10"],
            unblock=lambda serv_button_group: "group" not in serv_button_group,
        )
    ]
)
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
def test_custom_button_text_display(appliance, context, serv_button_group, service):
    """ Test custom button text display on option

    Bugzilla:
        * 1650066

    Polarion:
        assignee: ndhandre
        caseimportance: medium
        initialEstimate: 1/6h
        testSteps:
                1. Appliance with Service
                2. Create custom button `Group` or `Button` without display option
                3. Check Group/Button text display or not on UI and SSUI.
    """

    my_service = MyService(appliance, name=service.name)
    button, group = serv_button_group

    with appliance.context.use(context):
        navigate_to = ssui_nav if context is ViaSSUI else ui_nav
        destinations = (
            ["Details"]
            if (BZ(1650066, forced_streams=["5.9", "5.10"]).blocks and context is ViaSSUI)
            else ["All", "Details"]
        )
        for destination in destinations:
            view = navigate_to(my_service, destination)
            custom_button_group = Dropdown(view, group.text)
            if group.display is True:
                assert "" in custom_button_group.items
            else:
                assert custom_button_group.read() == ""


@pytest.fixture(params=["enablement", "visibility"], scope="module")
def vis_enb_button(request, appliance, button_group):
    """Create custom button with enablement/visibility expression"""
    group, _ = button_group
    exp = {request.param: {"tag": "My Company Tags : Department", "value": "Engineering"}}

    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            display_for="Single entity",
            system="Request",
            request="InspectMe",
            **exp
        )
    yield button, request.param
    button.delete_if_exists()


@pytest.mark.tier(0)
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.uncollectif(lambda context, button_group: "GENERIC" in button_group)
def test_custom_button_expression(appliance, context, objects, button_group, vis_enb_button):
    """ Test custom button as per expression enablement/visibility.

    Bugzilla:
        * 1509959, 1513498

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with expression (Tag)
                a. Enablement Expression
                b. Visibility Expression
            3. Navigate to object Detail page
            4. Check: button should not enable/visible without tag
            5. Check: button should enable/visible with tag
    """

    # ToDo: Add support for Generic Object by adding tagging ability from All page.
    group, obj_type = button_group
    button, expression = vis_enb_button
    obj = objects[obj_type]["Details"][0]
    dest_name = objects[obj_type]["Details"][1]
    navigate_to = ssui_nav if context is ViaSSUI else ui_nav
    tag_cat = appliance.collections.categories.instantiate(
        name="department", display_name="Department"
    )
    tag = tag_cat.collections.tags.instantiate(name="engineering", display_name="Engineering")

    # Check without tag
    with appliance.context.use(ViaUI):
        if tag.display_name in [item.display_name for item in obj.get_tags()]:
            obj.remove_tag(tag)

    with appliance.context.use(context):
        view = navigate_to(obj, dest_name)
        custom_button_group = (
            CustomButtonSSUIDropdwon(view, group.text)
            if context is ViaSSUI
            else Dropdown(view, group.text)
        )

        if expression == "enablement":
            # Note: SSUI still fallow enablement behaviour like 5.9. In latest version dropdown
            # having single button and button is disabled then dropdown disabled.
            if appliance.version < "5.10" or (context is ViaSSUI):
                assert not custom_button_group.item_enabled(button.text)
            else:
                assert not custom_button_group.is_enabled
        elif expression == "visibility":
                assert not custom_button_group.is_displayed

    # Check with tag
    with appliance.context.use(ViaUI):
        if tag.display_name not in [item.display_name for item in obj.get_tags()]:
            obj.add_tag(tag)

    with appliance.context.use(context):
        view = navigate_to(obj, dest_name)
        custom_button_group = (
            CustomButtonSSUIDropdwon(view, group.text)
            if context is ViaSSUI
            else Dropdown(view, group.text)
        )

        if expression == "enablement":
            assert custom_button_group.item_enabled(button.text)
        elif expression == "visibility":
                assert button.text in custom_button_group.items
