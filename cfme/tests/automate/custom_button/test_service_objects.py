import fauxfactory
import pytest
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.services.myservice import MyService
from cfme.tests.automate.custom_button import CustomButtonSSUIDropdwon
from cfme.tests.automate.custom_button import log_request_check
from cfme.tests.automate.custom_button import TextInputDialogSSUIView
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [pytest.mark.tier(2), test_requirements.custom_button]

GENERIC_SSUI_UNCOLLECT = "Generic object custom button not supported by SSUI"

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
def objects(appliance, add_generic_object_to_service):
    instance = add_generic_object_to_service
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


@pytest.fixture(params=OBJECTS, ids=[obj.capitalize() for obj in OBJECTS], scope="module")
def button_group(appliance, request):
    with appliance.context.use(ViaUI):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_alphanumeric(start="grp_"),
            hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
            type=getattr(collection, request.param),
        )
        yield button_gp, request.param
        button_gp.delete_if_exists()


@pytest.fixture(params=TEXT_DISPLAY, scope="module")
def serv_button_group(appliance, request):

    with appliance.context.use(ViaUI):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_numeric_string(start="grp_"),
            hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
            display=TEXT_DISPLAY[request.param]["group_display"],
            type=getattr(collection, "SERVICE"),
        )

        button = button_gp.buttons.create(
            text=fauxfactory.gen_numeric_string(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            display=TEXT_DISPLAY[request.param]["btn_display"],
            display_for="Single and list",
            system="Request",
            request="InspectMe",
        )
        yield button, button_gp
        button.delete_if_exists()
        button_gp.delete_if_exists()


# TODO(BZ-1755229): move to module scope as BZ fixed
@pytest.fixture(scope="function")
def service_button_group(appliance):
    with appliance.context.use(ViaUI):
        collection = appliance.collections.button_groups
        button_gp = collection.create(
            text=fauxfactory.gen_alphanumeric(start="group_"),
            hover=fauxfactory.gen_alphanumeric(start="hover_"),
            type=getattr(collection, "SERVICE"),
        )
        yield button_gp
        button_gp.delete_if_exists()


@pytest.fixture(params=["enablement", "visibility"])
def vis_enb_button_service(request, appliance, service_button_group):
    """Create custom button on service type object with enablement/visibility expression"""
    exp = {request.param: {"tag": "My Company Tags : Department", "value": "Engineering"}}

    with appliance.context.use(ViaUI):
        button = service_button_group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(start="hover_"),
            display_for="Single entity",
            system="Request",
            request="InspectMe",
            **exp
        )
        yield service_button_group, button, request.param
        button.delete_if_exists()


@pytest.mark.tier(1)
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.parametrize(
    "display",
    list(DISPLAY_NAV.keys()),
    ids=[item.replace(" ", "_") for item in DISPLAY_NAV.keys()]
)
@pytest.mark.uncollectif(lambda context, button_group:
                         context == ViaSSUI and "GENERIC" in button_group,
                         reason=GENERIC_SSUI_UNCOLLECT)
@pytest.mark.meta(
    automates=[1650066],
    blockers=[
        BZ(
            1650066,
            forced_streams=["5.11"],
            unblock=lambda display, context: not (
                context is ViaSSUI and display in ["List", "Single and list"]
            ),
        )
    ]
)
def test_custom_button_display_service_obj(
    request, appliance, context, display, objects, button_group
):
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
            3. Navigate to object type page as per display selected [For service SSUI]
            4. Single entity: Details page of the entity
            5. List: All page of the entity
            6. Single and list: Both All and Details page of the entity
            7. Check for button group and button

    Bugzilla:
        1650066
    """

    group, obj_type = button_group

    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(start="btn_hvr_"),
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
@pytest.mark.uncollectif(lambda context, button_group:
                         context == ViaSSUI and "GENERIC" in button_group,
                         reason=GENERIC_SSUI_UNCOLLECT)
def test_custom_button_automate_service_obj(
    request, appliance, context, submit, objects, button_group
):
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
            9. One by one: separate requests for all entities execution

    Bugzilla:
        1650066
    """

    group, obj_type = button_group
    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
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
            if context == ViaSSUI and BZ(1650066, forced_streams=["5.11"]).blocks
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
                diff = "executed" if appliance.version < "5.10" else "launched"
                view.flash.assert_message(f'"{button.text}" was {diff}')

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
        # for 5.10 group ui
        BZ(
            1659452,
            unblock=lambda serv_button_group, context: "button" in serv_button_group or
                                                       ("group" in serv_button_group and
                                                        context == ViaSSUI),
            forced_streams=['5.10']
        ),
        # for 5.10 and 5.11 group ssui
        BZ(
            1745492,
            unblock=lambda serv_button_group, context: "button" in serv_button_group
            or ("group" in serv_button_group and context == ViaUI),
        ),
    ],
    automates=[1659452, 1745492],
)
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
def test_custom_button_text_display(appliance, context, serv_button_group, gen_rest_service):
    """ Test custom button text display on option

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Appliance with Service
            2. Create custom button `Group` or `Button` without display option
            3. Check Group/Button text display or not on UI and SSUI.

    Bugzilla:
        1650066
        1659452
        1745492
    """

    my_service = MyService(appliance, name=gen_rest_service.name)
    button, group = serv_button_group

    with appliance.context.use(context):
        navigate_to = ssui_nav if context is ViaSSUI else ui_nav
        destinations = (
            ["Details"]
            if (BZ(1650066, forced_streams=["5.11"]).blocks and context is ViaSSUI)
            else ["All", "Details"]
        )
        for destination in destinations:
            view = navigate_to(my_service, destination)
            custom_button_group = Dropdown(view, group.hover if context is ViaUI else group.text)

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
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            display_for="Single entity",
            system="Request",
            request="InspectMe",
            **exp
        )
    yield button, request.param
    button.delete_if_exists()


@pytest.mark.tier(0)
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.uncollectif(lambda button_group:
                         "GENERIC" in button_group,
                         reason='Generic button group type not valid for test')
def test_custom_button_expression_service_obj(
    appliance, context, objects, button_group, vis_enb_button
):
    """ Test custom button as per expression enablement/visibility.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        casecomponent: CustomButton
        startsin: 5.9
        testSteps:
            1. Create custom button group with the Object type
            2. Create a custom button with expression (Tag)
                a. Enablement Expression
                b. Visibility Expression
            3. Navigate to object Detail page
            4. Check: button should not enable/visible without tag
            5. Check: button should enable/visible with tag

    Bugzilla:
        1509959
        1513498
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
        if tag in obj.get_tags():
            obj.remove_tag(tag)

    with appliance.context.use(context):
        view = navigate_to(obj, dest_name, wait_for_view=15)
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
        obj.add_tag(tag)  # add_tag checks if its there first

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


@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
def test_custom_button_role_access_service(
        context, request, appliance, user_self_service_role, gen_rest_service, service_button_group
):
    """Test custom button for role access of SSUI

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
            1. Create role by copying EvmRole-user_self_service
            2. Create Group and respective user for role
            3. Create custom button group
            4. Create custom button with role
            5. Check use able to access custom button or not
    """
    usr, role = user_self_service_role
    service = MyService(appliance, name=gen_rest_service.name)

    # custom button on group with role
    with appliance.context.use(ViaUI):
        btn = service_button_group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(start="hvr_"),
            system="Request",
            request="InspectMe",
            roles=[role.name],
        )
        request.addfinalizer(btn.delete_if_exists)

    # check button with admin and other user for UI and SSUI
    for user in [usr, appliance.user]:
        with user:
            with appliance.context.use(context):
                logged_in_page = appliance.server.login(user)

                if context is ViaSSUI:
                    navigate_to = ssui_nav
                    group_class = CustomButtonSSUIDropdwon
                else:
                    navigate_to = ui_nav
                    group_class = Dropdown

                view = navigate_to(service, 'Details')
                cb_group = group_class(view, service_button_group.text)

                if user == usr:
                    # for user having custom role EvmRole-user_self_service
                    assert cb_group.is_displayed
                    assert cb_group.has_item(btn.text)
                else:
                    # other user
                    assert (
                        not cb_group.is_displayed if context is ViaUI else cb_group.is_displayed
                    )
                    if context is ViaSSUI:
                        assert not cb_group.has_item(btn.text)
                logged_in_page.logout()


@test_requirements.customer_stories
@pytest.mark.meta(automates=[BZ(1439883)])
@pytest.mark.provider([VMwareProvider], selector=ONE)
@pytest.mark.uncollectif(lambda button_group:
                         "GENERIC" in button_group,
                         reason='Generic button group type not valid for test')
def test_custom_button_dialog_service_archived(
    request, appliance, provider, setup_provider, service_vm, button_group, dialog
):
    """ From Service OPS check if archive vms"s dialog invocation via custom button. ref: BZ1439883

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create a button at the service level with InspectMe method
            2. Create a service that contains 1 VM
            3. Remove this VM from the provider, resulting in a VM state of 'Archived'
            4. Go to the service and try to execute the button

    Bugzilla:
        1439883
    """
    service, vm = service_vm
    group, obj_type = button_group

    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(start="hover_"),
            dialog=dialog,
            system="Request",
            request="InspectMe",
        )
    request.addfinalizer(button.delete_if_exists)

    for with_vm in [True, False]:  # [vm, archive_vm]
        if not with_vm:
            # Make vm archive by deleting vm from provider side
            vm.mgmt.delete()
            vm.wait_for_vm_state_change(
                desired_state="archived", timeout=720, from_details=False, from_any_provider=True
            )

        for context in [ViaUI, ViaSSUI]:  # check execution with UI and SSUI
            with appliance.context.use(context):
                navigate_to = ssui_nav if context is ViaSSUI else ui_nav
                view = navigate_to(service, "Details")

                # execute button
                custom_button_group = Dropdown(view, group.text)
                custom_button_group.item_select(button.text)
                _dialog_view = TextInputDialogView if context is ViaUI else TextInputDialogSSUIView
                dialog_view = view.browser.create_view(_dialog_view, wait="10s")

                # start log check
                request_pattern = "Attributes - Begin"
                log = LogValidator(
                    "/var/www/miq/vmdb/log/automation.log", matched_patterns=[request_pattern]
                )
                log.start_monitoring()

                # submit dialog
                dialog_view.submit.click()

                # SSUI not support flash messages
                if context is ViaUI:
                    view.flash.assert_message("Order Request was Submitted")

                # Check for request in automation log
                try:
                    wait_for(
                        lambda: log.matches[request_pattern] == 1,
                        timeout=180,
                        message="wait for expected match count",
                        delay=5,
                    )
                except TimedOutError:
                    pytest.fail(f"Expected '1' requests; found '{log.matches[request_pattern]}'")


@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
@pytest.mark.uncollectif(lambda context, button_group:
                         context == ViaSSUI and "GENERIC" in button_group,
                         reason=GENERIC_SSUI_UNCOLLECT)
def test_custom_button_dialog_service_obj(
    appliance, dialog, request, context, objects, button_group
):
    """ Test custom button with dialog and InspectMe method

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
            2. Create a custom button with service dialog
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog and submit
            7. Check for the proper flash message related to button execution

    Bugzilla:
        1574774
    """
    group, obj_type = button_group
    with appliance.context.use(ViaUI):
        button = group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            dialog=dialog,
            system="Request",
            request="InspectMe",
        )
        request.addfinalizer(button.delete_if_exists)

    with appliance.context.use(context):
        navigate_to = ssui_nav if context is ViaSSUI else ui_nav

        obj = objects[obj_type]["Details"][0]
        dest_name = objects[obj_type]["Details"][1]
        view = navigate_to(obj, dest_name)
        custom_button_group = Dropdown(view, group.text)
        assert custom_button_group.has_item(button.text)

        # Clear the automation log
        assert appliance.ssh_client.run_command(
            'echo -n "" > /var/www/miq/vmdb/log/automation.log'
        )

        custom_button_group.item_select(button.text)
        _dialog_view = TextInputDialogView if context is ViaUI else TextInputDialogSSUIView
        dialog_view = view.browser.create_view(_dialog_view, wait="10s")
        assert dialog_view.service_name.fill("Custom Button Execute")
        dialog_view.submit.click()

        # SSUI not support flash messages
        if context is ViaUI:
            view.flash.assert_message("Order Request was Submitted")

        # check request in log
        try:
            wait_for(
                log_request_check,
                [appliance, 1],
                timeout=600,
                message="Check for expected request count",
                delay=20,
            )
        except TimedOutError:
            assert False, "Expected {count} requests not found in automation log".format(
                count=str(1)
            )


@pytest.fixture(params=["Service", "Provider"], scope="module")
def unassigned_btn_setup(request, appliance, provider, gen_rest_service):
    if request.param == "Service":
        obj = MyService(appliance, name=gen_rest_service.name)
        destinations = [ViaUI, ViaSSUI]
    else:
        # only service is different than other custom button object so selecting one i.e. provider
        obj = provider
        destinations = [ViaUI]

    gp = appliance.collections.button_groups.instantiate(
        text="[Unassigned Buttons]", hover="Unassigned buttons", type=request.param
    )
    yield obj, gp, destinations


@pytest.mark.provider([VMwareProvider], scope="module", selector=ONE)
def test_custom_button_unassigned_behavior_objs(
    appliance, setup_provider, unassigned_btn_setup, request
):
    """ Test unassigned custom button behavior

    Note: Service unassigned custom button should display on SSUI but not OPS UI.
    For other than service objects also follows same behaviour i.e. not display on OPS UI.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/6h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.8
        casecomponent: CustomButton
        testSteps:
            1. Create unassigned custom button on service and one other custom button object.
            2. Check destinations OPS UI should not display unassigned button but SSUI should.

    Bugzilla:
        1653195
    """

    obj, gp, destinations = unassigned_btn_setup

    with appliance.context.use(ViaUI):
        button = gp.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            system="Request",
            request="InspectMe",
        )
        assert button.exists
        request.addfinalizer(button.delete_if_exists)

    # check for button as per destination and UI.
    for dest in destinations:
        navigate_to = ssui_nav if dest is ViaSSUI else ui_nav

        with appliance.context.use(dest):
            view = navigate_to(obj, "Details")
            btn = Button(view, button.text)
            assert btn.is_displayed if dest is ViaSSUI else not btn.is_displayed


@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1628727])
@pytest.mark.parametrize("context", [ViaUI, ViaSSUI])
def test_custom_button_expression_ansible_service(
    appliance, context, vis_enb_button_service, order_ansible_service_in_ops_ui
):
    """ Test custom button on ansible service as per expression enablement/visibility.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: medium
        casecomponent: CustomButton
        startsin: 5.9
        testSteps:
            1. Create custom button group on Service object type
            2. Create a custom button with expression (Tag)
                a. Enablement Expression
                b. Visibility Expression
            3. Navigate to object Detail page
            4. Check: button should not enable/visible without tag
            5. Check: button should enable/visible with tag

    Bugzilla:
        1628727
        1509959
        1513498
        1755229
    """
    group, button, expression = vis_enb_button_service
    service = MyService(appliance, order_ansible_service_in_ops_ui)
    navigate_to = ssui_nav if context is ViaSSUI else ui_nav

    # tags
    tag_cat = appliance.collections.categories.instantiate(
        name="department", display_name="Department"
    )
    engineering_tag = tag_cat.collections.tags.instantiate(
        name="engineering", display_name="Engineering"
    )

    # check button expression with tag and without tag
    for tag in [False, True]:
        # manage tag
        with appliance.context.use(ViaUI):
            current_tag_status = engineering_tag in service.get_tags()
            if tag != current_tag_status:
                if tag:
                    service.add_tag(engineering_tag)
                else:
                    service.remove_tag(engineering_tag)

        # check expression
        with appliance.context.use(context):
            view = navigate_to(service, "Details", wait_for_view=15)
            custom_button_group = (
                CustomButtonSSUIDropdwon(view, group.text)
                if context is ViaSSUI
                else Dropdown(view, group.text)
            )

            if tag:
                if expression == "enablement":
                    assert custom_button_group.item_enabled(button.text)
                else:  # visibility
                    assert button.text in custom_button_group.items
            else:
                if expression == "enablement":
                    # Note: SSUI still follow enablement behaviour like 5.9. In latest version
                    # dropdown having single button and button is disabled then dropdown disabled.
                    if context is ViaSSUI:
                        assert not custom_button_group.item_enabled(button.text)
                    else:
                        assert not custom_button_group.is_enabled
                else:  # visibility
                    assert not custom_button_group.is_displayed
