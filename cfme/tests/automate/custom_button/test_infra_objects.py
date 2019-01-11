import pytest
import fauxfactory
from textwrap import dedent

from widgetastic_patternfly import Dropdown

from cfme.automate.explorer.domain import DomainCollection
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.tests.automate.custom_button import log_request_check, TextInputDialogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import TimedOutError, wait_for


pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]

INFRA_OBJECTS = ["PROVIDER", "HOSTS", "VM_INSTANCE", "TEMPLATE_IMAGE", "DATASTORES", "CLUSTERS"]

DISPLAY_NAV = {
    "Single entity": ["Details"],
    "List": ["All"],
    "Single and list": ["All", "Details"],
}

SUBMIT = ["Submit all", "One by one"]


@pytest.fixture(scope="module")
def cls(appliance):
    domain = appliance.collections.domains.create(
        name="domain_{}".format(fauxfactory.gen_alphanumeric(4)), enabled=True
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
        name="meth_{}".format(fauxfactory.gen_alphanumeric(4)),
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
        name="inst_{}".format(fauxfactory.gen_alphanumeric(4)),
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

    try:
        if obj_type == "PROVIDER":
            obj = provider
        elif obj_type == "VM_INSTANCE":
            obj = provider.appliance.provider_based_collection(provider).all()[0]
        elif obj_type == "TEMPLATE_IMAGE":
            obj = provider.appliance.collections.infra_templates.all()[0]
        else:
            obj = getattr(provider.appliance.collections, obj_type.lower()).all()[0]
    except IndexError:
        pytest.skip("Object not found for {obj} type".format(obj=obj_type))

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

    Polarion:
        assignee: ndhandre
        caseimportance: critical
        initialEstimate: 1/4h
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


@pytest.mark.parametrize("submit", SUBMIT, ids=["_".join(item.split()) for item in SUBMIT])
@pytest.mark.meta(
    blockers=[BZ(1628224, forced_streams=["5.10"], unblock=lambda submit: submit != "Submit all")]
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

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
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
        assert appliance.ssh_client.run_command(
            'echo -n "" > /var/www/miq/vmdb/log/automation.log'
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
                timeout=600,
                message="Check for expected request count",
                delay=20,
            )
        except TimedOutError:
            assert False, "Expected {} requests not found in automation log".format(
                str(expected_count)
            )


@pytest.mark.meta(
    blockers=[
        BZ(
            1641669,
            forced_streams=["5.9"],
            unblock=lambda button_group: "DATASTORES" not in button_group,
        )
    ]
)
def test_custom_button_dialog(appliance, dialog, request, setup_obj, button_group):
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
        * 1635797, 1555331, 1574403, 1640592, 1641669

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
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

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)
    assert custom_button_group.has_item(button.text)
    custom_button_group.item_select(button.text)

    dialog_view = view.browser.create_view(TextInputDialogView)
    dialog_view.wait_displayed()
    assert dialog_view.service_name.fill("Custom Button Execute")

    # Clear the automation log
    assert appliance.ssh_client.run_command('echo -n "" > /var/www/miq/vmdb/log/automation.log')

    # Submit order
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


@pytest.mark.parametrize("expression", ["enablement", "visibility"])
def test_custom_button_expression(appliance, request, setup_obj, button_group, expression):
    """ Test custom button as per expression enablement/visibility.

    prerequisites:
        * Appliance with Infra provider

    Steps:
        * Create custom button group with the Object type
        * Create a custom button with expression (Tag)
            1. Enablement Expression
            2. Visibility Expression
        * Navigate to object Detail page
        * Check: button should not enable/visible without tag
        * Check: button should enable/visible with tag

    Polarion:
        assignee: ndhandre
        caseimportance: high
        initialEstimate: 1/4h
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

    view = navigate_to(setup_obj, "Details")
    custom_button_group = Dropdown(view, group.hover)

    if tag.display_name in [item.display_name for item in setup_obj.get_tags()]:
        if expression == "enablement":
            assert custom_button_group.item_enabled(button.text)
            setup_obj.remove_tag(tag)
            if appliance.version < "5.10":
                assert not custom_button_group.item_enabled(button.text)
            else:
                assert not custom_button_group.is_enabled
        elif expression == "visibility":
            assert custom_button_group.is_displayed
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
            assert custom_button_group.is_displayed


@pytest.mark.uncollectif(lambda button_group: "VM_INSTANCE" not in button_group)
def test_open_url(request, setup_obj, button_group, method):
    """ Test Open url functionality of custom button.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2
        caseimportance: high
        testSteps:
            1. Appliance with Infra provider
            2. Create ruby method for url functionality
            3. Create custom button group with the Object type
            4. Create a custom button with open_url option and respective method
            5. Navigate to object Detail page
            6. Execute custom button
            7. Check new tab open or not with respective url
    """

    group, obj_type = button_group
    button = group.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
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
