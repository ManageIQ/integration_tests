import fauxfactory
import pytest

from cfme import test_requirements
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionDetailsView
from cfme.utils.update import update

pytestmark = [pytest.mark.tier(2), test_requirements.custom_button]


@pytest.fixture(scope="module")
def button_group(appliance, gen_definition):
    group = gen_definition.collections.generic_object_groups_buttons.create(
        name=fauxfactory.gen_numeric_string(13, start="btn_group", separator="-"),
        description=fauxfactory.gen_alphanumeric(start="disc", separator="-"),
        image="fa-user",
    )
    yield group
    group.delete_if_exists()


def test_custom_group_on_generic_class_crud(appliance, gen_definition):
    """ Test custom button group crud operation on generic class definition

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/8h
        caseimportance: critical
        startsin: 5.10
        casecomponent: CustomButton
        testSteps:
            1. Create custom button group on generic class
            2. Update custom button group by editing
            3. Delete custom button group
    """
    # create group
    group = gen_definition.collections.generic_object_groups_buttons.create(
        name=fauxfactory.gen_numeric_string(13, start="btn_group", separator="-"),
        description=fauxfactory.gen_alphanumeric(start="disc", separator="-"),
        image="fa-user",
    )
    view = appliance.browser.create_view(GenericObjectDefinitionDetailsView)
    assert view.flash.assert_success_message(
        f'Custom Button Group "{group.name}" has been successfully added.'
    )
    assert group.exists

    # update group
    with update(group):
        group.name = fauxfactory.gen_numeric_string(13, start="btn_group", separator="-")
        group.description = fauxfactory.gen_alphanumeric(start="disc", separator="-")
    assert view.flash.assert_success_message(
        f'Custom Button Group "{group.name}" has been successfully saved.'
    )
    assert group.exists

    # delete group
    group.delete()
    view.flash.assert_success_message('Button Group:"undefined" was successfully deleted')
    assert not group.exists


@pytest.mark.meta(automates=[1534539])
@pytest.mark.parametrize("btn_state", [True, False], ids=["with_group", "undefined"])
def test_custom_button_on_generic_class_crud(appliance, button_group, btn_state):
    """Test custom button crud operation on generic class definition

    Bugzilla:
        1534539

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/8h
        caseimportance: critical
        startsin: 5.10
        casecomponent: CustomButton
        testSteps:
            1. Create custom button on generic class (with group and undefined)
            2. Update custom button by editing
            3. Delete custom button
    """
    parent = button_group if btn_state else button_group.parent.parent

    # create button
    button = parent.collections.generic_object_buttons.create(
        name=fauxfactory.gen_numeric_string(start="btn", separator="-"),
        description=fauxfactory.gen_numeric_string(start="disc", separator="-"),
        image="fa-home",
        request="InspectMe",
    )
    view = appliance.browser.create_view(GenericObjectDefinitionDetailsView)
    assert view.flash.assert_success_message(
        f'Custom Button "{button.name}" has been successfully added.'
    )
    assert button.exists

    # update button
    with update(button):
        button.name = fauxfactory.gen_numeric_string(start="btn", separator="-")
        button.description = fauxfactory.gen_alphanumeric(start="disc", separator="-")
    assert view.flash.assert_success_message(
        f'Custom Button "{button.name}" has been successfully saved.'
    )
    assert button.exists

    # delete button
    button.delete()
    assert view.flash.assert_success_message('Button:"undefined" was successfully deleted')
    assert not button.exists
