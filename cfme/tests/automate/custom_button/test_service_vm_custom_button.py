from textwrap import dedent

import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.tests.automate.custom_button import DropdownDialogView
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav
from cfme.utils.log_validator import LogValidator


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.provider(
        [VMwareProvider],
        selector=ONE,
        required_fields=[["provisioning", "template"]],
        scope="module",
    ),
    pytest.mark.usefixtures("setup_provider_modscope"),
]


@pytest.fixture(scope="module")
def button_group(appliance):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        type=getattr(collection, "VM_INSTANCE"),
    )
    yield button_gp
    button_gp.delete_if_exists()


@pytest.fixture(scope="module")
def setup_dynamic_dialog(appliance, custom_instance):
    # Create custom instance with ruby method
    code = dedent(
        """
        @vm = $evm.root['vm']
        dialog_hash = {}
        dialog_hash[@vm.id] = @vm.name
        $evm.object['default_value'] = dialog_hash.first[0]
        $evm.object['values'] = dialog_hash
        """
    )
    instance = custom_instance(ruby_code=code)

    # Create dynamic dialog
    service_dialog = appliance.collections.service_dialogs
    dialog = fauxfactory.gen_alphanumeric(12, start="dialog_")
    ele_name = fauxfactory.gen_alphanumeric(start="ele_")

    element_data = {
        "element_information": {
            "ele_label": fauxfactory.gen_alphanumeric(15, start="ele_label_"),
            "ele_name": ele_name,
            "ele_desc": fauxfactory.gen_alphanumeric(15, start="ele_desc_"),
            "dynamic_chkbox": True,
            "choose_type": "Dropdown",
        },
        "options": {"entry_point": instance.tree_path, "field_required": True},
    }
    sd = service_dialog.create(label=dialog, description="my dialog")
    tab = sd.tabs.create(
        tab_label=fauxfactory.gen_alphanumeric(start="tab_"), tab_desc="my tab desc"
    )
    box = tab.boxes.create(
        box_label=fauxfactory.gen_alphanumeric(start="box_"), box_desc="my box desc"
    )
    box.elements.create(element_data=[element_data])

    yield sd, ele_name
    sd.delete_if_exists()


def test_custom_button_display_service_vm(request, appliance, service_vm, button_group):
    """ Test custom button display on UI and SSUI vm resource detail page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        setup:
            1. Order VM from service
        testSteps:
            1. Add custom button group for VM/Instance object from automation
            2. Add custom button in above group
            3. Navigate to VM Details page from service (UI and SSUI)
        expectedResults:
            1.
            2.
            3. Check for button group and button displayed or not

    Bugzilla:
        1427430
        1450473
    """

    service, _ = service_vm
    with appliance.context.use(ViaUI):
        button = button_group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            system="Request",
            request="InspectMe",
        )
        request.addfinalizer(button.delete_if_exists)

    # Check for UI and SSUI destinations.
    for context in [ViaUI, ViaSSUI]:
        with appliance.context.use(context):
            nav_to = ssui_nav if context is ViaSSUI else ui_nav

            # Navigate to VM Details page of service
            view = nav_to(service, "VMDetails")

            # Check button group and button displayed or not
            custom_button_group = Dropdown(view, button_group.text)
            assert custom_button_group.is_displayed
            assert custom_button_group.has_item(button.text)


@pytest.mark.customer_scenario
@test_requirements.customer_stories
@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1687061])
def test_custom_button_with_dynamic_dialog_vm(
    appliance, provider, request, service_vm, setup_dynamic_dialog
):
    """ Test custom button combination with dynamic dialog for VM entity.

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        testSteps:
            1. Create new domain and copy 'Request' class from ManageIQ domain
            2. Create class method under new domain with following ruby method
            ```ruby
              @vm = $evm.root['vm']
              dialog_hash = {}
              dialog_hash[@vm.id] = @vm.name
              $evm.object['default_value'] = dialog_hash.first[0]
              $evm.object['values'] = dialog_hash
            ```
            3. Create Instance Pointing class method
            4. Create Dropdown type Service Dialog (dynamic) with entry point as above method
            5. Create Custom button with Service Dialog on VM/Instance Object
            6. Execute button on VM with OPS UI and SSUI.
        expectedResults:
            1.
            2.
            3.
            4. Check service dialog created or not
            5.
            6. Check dialog should take vm/instance name automatically as per method.
               Check automation log for button execution.

    Bugzilla:
        1687061
        1722817
        1729594
    """
    dialog, ele_name = setup_dynamic_dialog
    # Create button group
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(start="grp_"),
        hover=fauxfactory.gen_alphanumeric(15, start="grp_hvr_"),
        type=getattr(collection, "VM_INSTANCE"),
    )
    request.addfinalizer(button_gp.delete_if_exists)

    # Create custom button under group
    button = button_gp.buttons.create(
        text=fauxfactory.gen_alphanumeric(start="btn_"),
        hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
        dialog=dialog.label,
        system="Request",
        request="InspectMe",
    )
    request.addfinalizer(button.delete_if_exists)

    # Check service vm on UI and SSUI
    service, _ = service_vm

    for context in [ViaUI, ViaSSUI]:
        with appliance.context.use(context):
            nav_to = ssui_nav if context is ViaSSUI else ui_nav

            # Navigate to VM Details page of service
            view = nav_to(service, "VMDetails")

            # Select button from custom button group dropdown
            custom_button_group = Dropdown(view, button_gp.text)
            assert custom_button_group.is_displayed
            custom_button_group.item_select(button.text)

            # Check default selected vm must destination vm
            view = view.browser.create_view(DropdownDialogView)
            serv = view.service_name(ele_name)
            serv.dropdown.wait_displayed()
            assert serv.dropdown.selected_option == service.vm_name

            # execute button and check `InspectMe` method by Attributes - Begin` and
            # `$evm.root['vm']` of dynamic dialog by expected service vm name in automation log
            log = LogValidator(
                "/var/www/miq/vmdb/log/automation.log",
                matched_patterns=["Attributes - Begin", f'name = "{service.vm_name}"'],
            )
            log.start_monitoring()
            submit = "submit" if context is ViaUI else "submit_request"
            getattr(view, submit).click()
            assert log.validate(wait="120s")


@pytest.mark.meta(automates=[1427430, 1450473, 1454910])
def test_custom_button_automate_service_vm(request, appliance, service_vm, button_group):
    """ Test custom button execution on SSUI vm resource detail page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2h
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button

    Bugzilla:
        1427430
        1450473
        1454910
    """

    service, _ = service_vm
    with appliance.context.use(ViaUI):
        button = button_group.buttons.create(
            text=fauxfactory.gen_alphanumeric(start="btn_"),
            hover=fauxfactory.gen_alphanumeric(15, start="btn_hvr_"),
            system="Request",
            request="InspectMe",
        )
        request.addfinalizer(button.delete_if_exists)

    # Check for UI and SSUI destinations.
    for context in [ViaUI, ViaSSUI]:
        with appliance.context.use(context):
            nav_to = ssui_nav if context is ViaSSUI else ui_nav

            # Navigate to VM Details page of service
            view = nav_to(service, "VMDetails")

            # start log check
            log = LogValidator(
                "/var/www/miq/vmdb/log/automation.log", matched_patterns=["Attributes - Begin"]
            )
            log.start_monitoring()

            # Execute custom button on service vm
            custom_button_group = Dropdown(view, button_group.text)
            custom_button_group.item_select(button.text)

            # validate request in log
            assert log.validate(wait="120s")
