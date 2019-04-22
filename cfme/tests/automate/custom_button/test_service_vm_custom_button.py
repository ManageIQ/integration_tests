import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance import ViaSSUI
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ssui import navigate_to as ssui_nav
from cfme.utils.appliance.implementations.ui import navigate_to as ui_nav


pytestmark = [
    pytest.mark.tier(2),
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
