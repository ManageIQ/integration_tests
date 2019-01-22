import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check, OBJ_TYPE_59, TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([OpenStackProvider], selector=ONE_PER_TYPE),
]

CLOUD_OBJECTS = [
    "PROVIDER",
    "VM_INSTANCE",
    "TEMPLATE_IMAGE",
    "AZONE",
    "CLOUD_NETWORK",
    "CLOUD_SUBNET",
    "SECURITY_GROUP",
    "ROUTER",
    "CLOUD_OBJECT_STORE_CONTAINER",
]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]


@pytest.fixture(
    params=CLOUD_OBJECTS, ids=[obj.capitalize() for obj in CLOUD_OBJECTS], scope="module"
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
def setup_objs(button_group, provider):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    if obj_type == "PROVIDER":
        # Note: For the custom button provider object points
        # provider, storage managers, network managers
        block_coll = provider.appliance.collections.block_managers.filter({"provider": provider})
        block_manager = block_coll.all()[0]
        object_coll = provider.appliance.collections.object_managers.filter({"provider": provider})
        object_manager = object_coll.all()[0]
        network_manager = provider.appliance.collections.network_providers.all()[0]
        obj = [provider, network_manager, block_manager, object_manager]
    elif obj_type == "VM_INSTANCE":
        obj = [provider.appliance.provider_based_collection(provider).all()[0]]
    elif obj_type == "TEMPLATE_IMAGE":
        obj = [provider.appliance.collections.cloud_images.all()[0]]
    elif obj_type == "AZONE":
        obj = [
            provider.appliance.collections.cloud_av_zones.filter({"provider": provider}).all()[0]
        ]
    elif obj_type == "CLOUD_SUBNET":
        obj = [provider.appliance.collections.network_subnets.all()[0]]
    elif obj_type == "SECURITY_GROUP":
        obj = [provider.appliance.collections.network_security_groups.all()[0]]
    elif obj_type == "ROUTER":
        obj = [provider.appliance.collections.network_routers.all()[0]]
    elif obj_type == "CLOUD_OBJECT_STORE_CONTAINER":
        obj = [
            provider.appliance.collections.object_store_containers.filter(
                {"provider": provider}
            ).all()[0]
        ]
    elif obj_type == "CLOUD_NETWORK":
        obj = [provider.appliance.collections.cloud_networks.all()[0]]
    else:
        logger.error("No object collected for custom button object type '{}'".format(obj_type))
    return obj


@pytest.mark.tier(1)
@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(appliance, request, display, setup_objs, button_group):
    """ Test custom button display on a targeted page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: custom_button
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

    for setup_obj in setup_objs:
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
def test_custom_button_dialog(appliance, dialog, request, setup_objs, button_group):
    """ Test custom button with dialog and InspectMe method

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
        tags: custom_button
        testSteps:
            1. Simple TextInput service dialog
            2. Create custom button group with the Object type
            3. Create a custom button with service dialog
            4. Navigate to object Details page
            5. Check for button group and button
            6. Select/execute button from group dropdown for selected entities
            7. Fill dialog and submit
            8. Check for the proper flash message related to button execution

    Bugzilla:
        1635797, 1555331, 1574403, 1640592
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

    for setup_obj in setup_objs:
        view = navigate_to(setup_obj, "Details")
        custom_button_group = Dropdown(view, group.hover)
        assert custom_button_group.has_item(button.text)
        custom_button_group.item_select(button.text)

        dialog_view = view.browser.create_view(TextInputDialogView, wait="10s")
        dialog_view.service_name.fill("Custom Button Execute")

        # Clear the automation log
        assert appliance.ssh_client.run_command(
            'echo -n "" > /var/www/miq/vmdb/log/automation.log'
        )

        # Submit order request
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
@pytest.mark.parametrize("submit", SUBMIT, ids=[item.replace(" ", "_") for item in SUBMIT])
def test_custom_button_automate(appliance, request, submit, setup_objs, button_group):
    """ Test custom button for automate and requests count as per submit

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
        tags: custom_button
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with specific submit option and Single and list display
            3. Navigate to object type pages (All and Details)
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Check for the proper flash message related to button execution
            7. Check automation log requests. Submitted as per selected submit option or not.
            8. Submit all: single request for all entities execution
            9 One by one: separate requests for all entities execution

    Bugzilla:
        1628224, 1642147
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
    for setup_obj in setup_objs:
        for destination in ["All", "Details"]:
            obj = setup_obj.parent if destination == "All" else setup_obj

            view = navigate_to(obj, destination)
            custom_button_group = Dropdown(view, group.hover)
            assert custom_button_group.has_item(button.text)

            # Entity count depends on the destination for `All` available entities and
            # `Details` means a single entity.
            # To-Do: remove Manager check as BZ-1642147 fix
            if destination == "All":
                try:
                    paginator = view.paginator
                except AttributeError:
                    paginator = view.entities.paginator
                entity_count = min(paginator.items_amount, paginator.items_per_page)

                # Work around for  BZ-1642147
                try:
                    if "Manager" in setup_obj.name:
                        entity_count = 1
                except AttributeError:
                    pass

                paginator.check_all()
            else:
                entity_count = 1

            # Clear the automation log
            assert appliance.ssh_client.run_command(
                'echo -n "" > ' "/var/www/miq/vmdb/log/automation.log"
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
                    timeout=300,
                    message="Check for expected request count",
                    delay=10,
                )
            except TimedOutError:
                assert False, "Expected {} requests not found in automation log".format(
                    str(expected_count)
                )


@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression(appliance, request, setup_objs, button_group, expression):
    """ Test custom button as per expression enablement/visibility.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: custom_button
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

    for setup_obj in setup_objs:
        view = navigate_to(setup_obj, "Details")
        custom_button_group = Dropdown(view, group.hover)

        # Note: For higher version (5.10+), button group having single button;
        # If button is disabled then group disabled.

        if tag.display_name in [item.display_name for item in setup_obj.get_tags()]:
            if expression == "enablement":
                assert custom_button_group.item_enabled(button.text)
                setup_obj.remove_tag(tag)
                if appliance.version < "5.10":
                    assert not custom_button_group.item_enabled(button.text)
                else:
                    assert not custom_button_group.is_enabled
            elif expression == "visibility":
                assert button.text in custom_button_group.items
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
                assert button.text in custom_button_group.items
