import pytest
import fauxfactory

from widgetastic_patternfly import Dropdown

from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check, TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
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

OBJ_TYPE_59 = [
    "CLOUD_TENANT",
    "CLOUD_VOLUME",
    "CLUSTER",
    "CONTAINER_NODE",
    "CONTAINER_PROJECT",
    "DATASTORE",
    "GENERIC",
    "HOST",
    "PROVIDER",
    "SERVICE",
    "TEMPLATE_IMAGE",
    "VM_INSTANCE",
]


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


@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display(appliance, request, display, setup_objs, button_group):
    """ Test custom button display on a targeted page

    prerequisites:
        * Appliance with Cloud provider

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
@pytest.mark.meta(
    blockers=[
        BZ(
            1635797,
            forced_streams=["5.9", "5.10"],
            unblock=lambda button_group: bool(
                [
                    obj
                    for obj in ["PROVIDER", "VM_INSTANCE", "CLOUD_NETWORK"]
                    if obj in button_group
                ]
            ),
        )
    ]
)
def test_custom_button_dialog(appliance, dialog, request, setup_objs, button_group):
    """ Test custom button with dialog and InspectMe method

    Prerequisites:
        * Appliance with Infra provider
        * Simple TextInput service dialog

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with service dialog
        * Navigate to object Details page
        * Check for button group and button
        * Select/execute button from group dropdown for selected entities
        * Fill dialog and submit
        * Check for the proper flash message related to button execution

    Bugzillas:
        * 1635797, 1555331, 1574403
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

        dialog_view = view.browser.create_view(TextInputDialogView)
        dialog_view.wait_displayed()
        dialog_view.service_name.fill("Custom Button Execute")

        # Clear the automation log
        assert appliance.ssh_client.run_command(
            'echo -n "" > /var/www/miq/vmdb/log/automation.log'
        )

        # Submit order request
        dialog_view.submit.click()

        if not (
            BZ(bug_id=1640592, forced_streams=["5.9", "5.10"]).blocks
            and obj_type == "TEMPLATE_IMAGE"
        ):
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


@pytest.mark.meta(
    blockers=[BZ(1628224, forced_streams=["5.10"], unblock=lambda submit: submit != "Submit all")]
)
@pytest.mark.uncollectif(
    lambda appliance, button_group: not bool([obj for obj in OBJ_TYPE_59 if obj in button_group])
    and appliance.version < "5.10"
)
@pytest.mark.parametrize("submit", SUBMIT, ids=["_".join(item.split()) for item in SUBMIT])
def test_custom_button_automate(appliance, request, submit, setup_objs, button_group):
    """ Test custom button for automate and requests count as per submit
    prerequisites:
        * Appliance with Cloud provider
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
        * 1628224, 1642147
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
            clean = appliance.ssh_client.run_command(
                'echo -n "" > ' "/var/www/miq/vmdb/log/automation.log"
            )
            assert clean.success
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
