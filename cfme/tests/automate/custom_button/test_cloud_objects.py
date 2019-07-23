import re

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check
from cfme.tests.automate.custom_button import OBJ_TYPE_59
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
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
def test_custom_button_display_cloud_obj(appliance, request, display, setup_objs, button_group):
    """ Test custom button display on a targeted page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: critical
        caseposneg: positive
        testtype: functional
        startsin: 5.8
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
def test_custom_button_dialog_cloud_obj(appliance, dialog, request, setup_objs, button_group):
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
            1. Simple TextInput service dialog
            2. Create custom button group with the Object type
            3. Create a custom button with service dialog
            4. Navigate to object Details page
            5. Check for button group and button
            6. Select/execute button from group dropdown for selected entities
            7. Fill dialog and submit
            8. Check for the proper flash message related to button execution

    Bugzilla:
        1635797
        1555331
        1574403
        1640592
        1710350
        1732436
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

        if not (BZ(1732436, forced_streams=["5.10", "5.11"]).blocks and obj_type == "PROVIDER"):
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
def test_custom_button_automate_cloud_obj(appliance, request, submit, setup_objs, button_group):
    """ Test custom button for automate and requests count as per submit

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
            2. Create a custom button with specific submit option and Single and list display
            3. Navigate to object type pages (All and Details)
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Check for the proper flash message related to button execution
            7. Check automation log requests. Submitted as per selected submit option or not.
            8. Submit all: single request for all entities execution
            9 One by one: separate requests for all entities execution

    Bugzilla:
        1628224
        1642147
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

            diff = "executed" if appliance.version < "5.10" else "launched"
            view.flash.assert_message('"{btn}" was {diff}'.format(btn=button.text, diff=diff))

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
def test_custom_button_expression_cloud_obj(
    appliance, request, setup_objs, button_group, expression
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

    for setup_obj in setup_objs:
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


@pytest.mark.meta(
    blockers=[BZ(1680525, unblock=lambda button_group: "CLOUD_NETWORK" not in button_group)]
)
@pytest.mark.parametrize("btn_dialog", [False, True], ids=["simple", "dialog"])
def test_custom_button_events_cloud_obj(request, dialog, setup_objs, button_group, btn_dialog):
    """Test custom button events

    Polarion:
        assignee: ndhandre
        caseimportance: medium
        initialEstimate: 1/4h
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create a Button Group
            2. Create custom button [with dialog/ without dialog]
            2. Execute button from respective location
            3. Assert event count

    Bugzilla:
        1668023
        1702490
        1680525
    """
    group, obj_type = button_group
    dialog_ = dialog if btn_dialog else None

    button = group.buttons.create(
        text="btn_{}".format(fauxfactory.gen_alphanumeric(3)),
        hover="btn_hover{}".format(fauxfactory.gen_alphanumeric(3)),
        dialog=dialog_,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    for setup_obj in setup_objs:
        initial_count = len(setup_obj.get_button_events())
        view = navigate_to(setup_obj, "Details")
        custom_button_group = Dropdown(view, group.hover)
        custom_button_group.item_select(button.text)

        if btn_dialog:
            dialog_view = view.browser.create_view(TextInputDialogView, wait="10s")
            dialog_view.submit.click()

        view.browser.refresh()
        current_count = len(setup_obj.get_button_events())
        assert current_count == (initial_count + 1)
