import fauxfactory
import pytest
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.custom_button,
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE),
]


@pytest.fixture(scope="function")
def setup_groups_buttons(appliance, provider):
    collection = appliance.collections.button_groups
    gp_buttons = {}

    for obj_type in ["PROVIDER", "VM_INSTANCE"]:
        gp = collection.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            type=getattr(collection, obj_type, None),
        )

        button = gp.buttons.create(
            text=fauxfactory.gen_alphanumeric(),
            hover=fauxfactory.gen_alphanumeric(),
            display_for="Single and list",
            system="Request",
            request="InspectMe",
        )

        if obj_type == "PROVIDER":
            obj = provider
        else:
            try:
                obj = appliance.provider_based_collection(provider).all()[0]
            except IndexError:
                pytest.skip("VM object not collected")

        gp_buttons[obj_type] = [gp, button, obj]

    yield gp_buttons

    for button_group in gp_buttons.values():
        grp_, button_, _ = button_group
        button_.delete_if_exists()
        grp_.delete_if_exists()


def checks(obj_type_conf):
    for obj_type, conf in obj_type_conf.items():
        gp, button, obj = conf
        obj.browser.refresh()  # before start checks refresh browser
        assert gp.exists
        assert button.exists

        view = navigate_to(button, "Details")
        assert view.text.text == button.text
        assert view.hover.text == button.hover

        for destination in ["All", "Details"]:
            # Note: For VM, custom button not display on All page but only VM page.
            nav_obj = obj.parent if destination == "All" else obj
            if obj_type == "VM_INSTANCE" and destination == "All":
                destination = "VMsOnly"

            view = navigate_to(nav_obj, destination)
            custom_button_group = Dropdown(view, gp.hover)
            assert custom_button_group.is_displayed
            assert custom_button_group.has_item(button.text)


@pytest.mark.post_upgrade
def test_custom_button_import_export(appliance, setup_groups_buttons):
    """ Test custom button display on a targeted page

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/2h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Create custom buttons and groups
            2. Check for custom buttons in respective implementation location
            3. Export created custom buttons using rake command
                `rake evm:export:custom_buttons -- --directory /tmp/custom_buttons`
            4. Clean all created buttons and groups
            5. Check properly clean up or not
            6. Import exported custom button yaml file using import rake command
                `rake evm:import:custom_buttons -- --source /tmp/custom_buttons`
            7. Check for custom buttons and groups which was exported comes back to UI or not
            8. Check for custom buttons in respective implementation location
    """

    # Check all buttons, groups and respective display at respective locations
    checks(setup_groups_buttons)

    # Export custom buttons
    dir_ = appliance.ssh_client.run_command("mkdir /tmp/custom_buttons")
    assert dir_.success
    export = appliance.ssh_client.run_command(
        "cd /var/www/miq/vmdb/; rake evm:export:custom_buttons -- --directory /tmp/custom_buttons"
    )
    assert export.success

    # clean up custom groups and button
    for conf in setup_groups_buttons.values():
        gp, button, _ = conf
        button.delete()
        assert not button.exists

        gp.delete()
        assert not gp.exists

    # Import custom buttons
    import_ = appliance.ssh_client.run_command(
        "cd /var/www/miq/vmdb/; rake evm:import:custom_buttons -- --source /tmp/custom_buttons"
    )
    assert import_.success

    # Check all buttons, groups and respective display at respective locations
    checks(setup_groups_buttons)
