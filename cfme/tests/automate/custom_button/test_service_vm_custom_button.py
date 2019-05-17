import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.provider([VMwareProvider], selector=ONE, scope="module"),
    pytest.mark.usefixtures("setup_provider_modscope"),
]


@pytest.fixture(scope="module")
def button_group(appliance):
    collection = appliance.collections.button_groups
    button_gp = collection.create(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=getattr(collection, "VM_INSTANCE"),
    )
    yield button_gp
    button_gp.delete_if_exists()


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
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
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


@test_requirements.customer_stories
@pytest.mark.manual
@pytest.mark.tier(1)
def test_custom_button_with_dynamic_dialog_vm():
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
    """
    pass
