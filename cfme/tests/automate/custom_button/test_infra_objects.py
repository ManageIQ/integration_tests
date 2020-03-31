import re
from textwrap import dedent

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]

INFRA_OBJECTS = [
    "PROVIDER",
    "HOSTS",
    "VM_INSTANCE",
    "TEMPLATE_IMAGE",
    "DATASTORES",
    "CLUSTERS",
    "SWITCH",
]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]


@pytest.fixture(scope="module")
def cls(appliance):
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alphanumeric(12, start="domain_"), enabled=True
    )
    original_class = (
        domain.parent.instantiate(name="ManageIQ")
        .namespaces.instantiate(name="System")
        .classes.instantiate(name="Request")
    )
    original_class.copy_to(domain=domain)
    yield domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")
    if domain.exists:
        domain.delete()


@pytest.fixture(scope="module")
def method(cls):
    meth = cls.methods.create(
        name=fauxfactory.gen_alphanumeric(start="meth_"),
        script=dedent(
            """
            # add google url to open
            vm = $evm.root['vm']
            $evm.log(:info, "Opening url")
            vm.remote_console_url = "http://example.com"
            """
        ),
    )

    instance = cls.instances.create(
        name=fauxfactory.gen_alphanumeric(start="inst_"),
        fields={"meth1": {"value": meth.name}},
    )
    yield instance
    meth.delete_if_exists()
    instance.delete_if_exists()


@pytest.fixture(
    params=INFRA_OBJECTS, ids=[obj.capitalize() for obj in INFRA_OBJECTS], scope="module"
)
def button_group(appliance, request):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        type=getattr(collection, request.param),
    )
    yield button_gp, request.param
    button_gp.delete_if_exists()


@pytest.fixture()
def setup_obj(button_group, provider):
    """ Setup object for specific custom button object type."""
    obj_type = button_group[1]

    try:
        if obj_type == "PROVIDER":
            obj = provider
        elif obj_type == "VM_INSTANCE":
            obj = provider.appliance.provider_based_collection(provider).all()[0]
        elif obj_type == "TEMPLATE_IMAGE":
            obj = provider.appliance.collections.infra_templates.all()[0]
        elif obj_type == "SWITCH":
            obj = provider.appliance.collections.infra_switches.all()[0]
        else:
            obj = getattr(provider.appliance.collections, obj_type.lower()).all()[0]
    except IndexError:
        pytest.skip(f"Object not found for {obj_type} type")

    return obj


@pytest.mark.tier(1)
@pytest.mark.parametrize(
    "display", DISPLAY_NAV.keys(), ids=["_".join(item.split()) for item in DISPLAY_NAV.keys()]
)
def test_custom_button_display_infra_obj(request, display, setup_obj, button_group):
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
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
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


@pytest.mark.parametrize("submit", SUBMIT, ids=["_".join(item.split()) for item in SUBMIT])
def test_custom_button_automate_infra_obj(appliance, request, submit, setup_obj, button_group):
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
        1628224
    """

    group, obj_type = button_group
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
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

        # start log check
        request_pattern = "Attributes - Begin"
        log = LogValidator(
            "/var/www/miq/vmdb/log/automation.log", matched_patterns=[request_pattern]
        )
        log.start_monitoring()

        custom_button_group.item_select(button.text)

        diff = "executed" if appliance.version < "5.10" else "launched"
        view.flash.assert_message(f'"{button.text}" was {diff}')

        # Submit all: single request for all entity execution
        # One by one: separate requests for all entity execution

        expected_count = 1 if submit == "Submit all" else entity_count

        try:
            wait_for(
                lambda: log.matches[request_pattern] == expected_count,
                timeout=300,
                message="wait for expected match count",
                delay=5,
            )
        except TimedOutError:
            assert False, "Expected '{}' requests and '{}' requests found in automation log".format(
                expected_count, log.matches[request_pattern]
            )


@pytest.mark.meta(
    blockers=[BZ(1685555,
                 unblock=lambda button_group: "SWITCH" not in button_group)]
)
def test_custom_button_dialog_infra_obj(appliance, dialog, request, setup_obj, button_group):
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
            1. Create custom button group with the Object type
            2. Create a custom button with service dialog
            3. Navigate to object Details page
            4. Check for button group and button
            5. Select/execute button from group dropdown for selected entities
            6. Fill dialog and submit
            7. Check for the proper flash message related to button execution

    Bugzilla:
        1635797
        1555331
        1574403
        1640592
        1641669
        1685555
    """

    group, obj_type = button_group

    # Note: No need to set display_for dialog only work with Single entity
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
        dialog=dialog,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(TextInputDialogView, wait="10s")
    assert dialog_view.service_name.fill("Custom Button Execute")

    # start log check
    request_pattern = "Attributes - Begin"
    log = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[request_pattern]
    )
    log.start_monitoring()

    # Submit order
    dialog_view.submit.click()
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
        assert False, "Expected '1' requests and '{}' requests found in automation log".format(
            log.matches[request_pattern]
        )


@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression_infra_obj(
    appliance, request, setup_obj, button_group, expression
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

    Bugzilla:
        1705141
    """

    group, obj_type = button_group
    exp = {expression: {"tag": "My Company Tags : Department", "value": "Engineering"}}
    disabled_txt = "Tag - My Company Tags : Department : Engineering"
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
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


@pytest.mark.uncollectif(lambda button_group: "VM_INSTANCE" not in button_group,
                         reason='Test only valid for VM_INSTANCE button group type')
def test_custom_button_open_url_infra_obj(request, setup_obj, button_group, method):
    """ Test Open url functionality of custom button.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Appliance with Infra provider
            2. Create ruby method for url functionality
            3. Create custom button group with the Object type
            4. Create a custom button with open_url option and respective method
            5. Navigate to object Detail page
            6. Execute custom button
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6. New tab should open with respective url
    """

    group, obj_type = button_group
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        open_url=True,
        display_for="Single entity",
        system="Request",
        request=method.name,
    )
    request.addfinalizer(button.delete_if_exists)

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)

    # TODO: Move windows handling functionality to browser
    initial_count = len(view.browser.selenium.window_handles)
    main_window = view.browser.selenium.current_window_handle
    custom_button_group.item_select(button.text)

    wait_for(
        lambda: len(view.browser.selenium.window_handles) > initial_count,
        timeout=120,
        message="Check for window open",
    )
    open_url_window = set(view.browser.selenium.window_handles) - {main_window}

    view.browser.selenium.switch_to_window(open_url_window.pop())

    @request.addfinalizer
    def _reset_window():
        if view.browser.selenium.current_window_handle != main_window:
            view.browser.selenium.close()
            view.browser.selenium.switch_to_window(main_window)

    assert "example.com" in view.browser.url


@pytest.mark.meta(
    blockers=[
        BZ(
            1685555,
            unblock=lambda button_group, btn_dialog: not ("SWITCH" in button_group and btn_dialog),
        ),
    ]
)
@pytest.mark.parametrize("btn_dialog", [False, True], ids=["simple", "dialog"])
def test_custom_button_events_infra_obj(request, dialog, setup_obj, button_group, btn_dialog):
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
        1685555
    """
    group, obj_type = button_group
    dialog_ = dialog if btn_dialog else None

    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
        dialog=dialog_,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)
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
