import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.generic_objects.definition.definition_views import GenericObjectDefinitionDetailsView
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


pytestmark = [pytest.mark.tier(2), test_requirements.custom_button]


@pytest.fixture(scope="module")
def generic_object_button(appliance, generic_object_button_group, generic_definition):
    def _generic_object_button(button_group):
        with appliance.context.use(ViaUI):
            button_parent = (
                generic_object_button_group(button_group) if button_group else generic_definition
            )
            button_name = 'button_{}'.format(fauxfactory.gen_alphanumeric())
            button_desc = 'Button_description_{}'.format(fauxfactory.gen_alphanumeric())
            generic_object_button = button_parent.collections.generic_object_buttons.create(
                name=button_name,
                description=button_desc,
                image='fa-home',
                request=fauxfactory.gen_alphanumeric()
            )
            view = appliance.browser.create_view(BaseLoggedInPage)
            view.flash.assert_no_error()
        return generic_object_button
    return _generic_object_button


@pytest.fixture(scope="module")
def generic_object_button_group(appliance, generic_definition):
    def _generic_object_button_group(create_action=True):
        if create_action:
            with appliance.context.use(ViaUI):
                group_name = "button_group_{}".format(fauxfactory.gen_alphanumeric())
                group_desc = "Group_button_description_{}".format(fauxfactory.gen_alphanumeric())
                groups_buttons = generic_definition.collections.generic_object_groups_buttons
                generic_object_button_group = groups_buttons.create(
                    name=group_name, description=group_desc, image="fa-user"
                )
                view = appliance.browser.create_view(BaseLoggedInPage)
                view.flash.assert_no_error()
            return generic_object_button_group

    return _generic_object_button_group


@pytest.fixture(scope="module")
def button_group(appliance, generic_definition):
    with appliance.context.use(ViaUI):
        group = generic_definition.collections.generic_object_groups_buttons.create(
            name=fauxfactory.gen_numeric_string(13, start="btn_group", separator="-"),
            description=fauxfactory.gen_alphanumeric(start="disc", separator="-"),
            image="fa-user",
        )
        yield group
        group.delete_if_exists()


@pytest.mark.meta(automates=[1744478])
def test_custom_group_on_generic_class_crud(appliance, generic_definition):
    """ Test custom button group crud operation on generic class definition

    Bugzilla:
        1744478

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

    with appliance.context.use(ViaUI):
        # create group
        group = generic_definition.collections.generic_object_groups_buttons.create(
            name=fauxfactory.gen_numeric_string(13, start="btn_group", separator="-"),
            description=fauxfactory.gen_alphanumeric(start="disc", separator="-"),
            image="fa-user",
        )
        view = appliance.browser.create_view(GenericObjectDefinitionDetailsView)
        view.flash.assert_success_message(
            f'Custom Button Group "{group.name}" has been successfully added.'
        )
        assert group.exists

        # update group
        with update(group):
            group.name = fauxfactory.gen_numeric_string(13, start="btn_group", separator="-")
            group.description = fauxfactory.gen_alphanumeric(start="disc", separator="-")
        view.flash.assert_success_message(
            f'Custom Button Group "{group.name}" has been successfully saved.'
        )
        assert group.exists

        # delete group
        group.delete()
        # TODO(ndhandre): For now, we can not guess exact flash message.
        #  Change flash as per BZ-1744478.
        view.flash.assert_success_message('Button Group:"undefined" was successfully deleted')
        assert not group.exists


@pytest.mark.meta(automates=[1534539, 1744478])
@pytest.mark.parametrize("is_undefined", [True, False], ids=["undefined", "with_group"])
def test_custom_button_on_generic_class_crud(appliance, button_group, is_undefined):
    """Test custom button crud operation on generic class definition

    Bugzilla:
        1534539
        1744478

    Polarion:
        assignee: ndhandre
        initialEstimate: 1/4h
        caseimportance: critical
        startsin: 5.10
        casecomponent: CustomButton
        testSteps:
            1. Create custom button on generic class (with group and undefined)
            2. Update custom button by editing
            3. Delete custom button
    """
    parent = button_group.parent.parent if is_undefined else button_group

    with appliance.context.use(ViaUI):
        # create button
        button = parent.collections.generic_object_buttons.create(
            name=fauxfactory.gen_numeric_string(start="btn", separator="-"),
            description=fauxfactory.gen_numeric_string(start="disc", separator="-"),
            image="fa-home",
            request="InspectMe",
        )
        view = appliance.browser.create_view(GenericObjectDefinitionDetailsView)

        if is_undefined:
            msg = f'Custom Button "{button.name}" has been successfully added.'
        else:
            msg = (
                f'Custom Button "{button.name}" has been successfully added '
                f"under the selected button group."
            )

        view.flash.assert_success_message(msg)
        assert button.exists

        # update button
        with update(button):
            button.name = fauxfactory.gen_numeric_string(start="btn", separator="-")
            button.description = fauxfactory.gen_alphanumeric(start="disc", separator="-")
        view.flash.assert_success_message(
            f'Custom Button "{button.name}" has been successfully saved.'
        )
        assert button.exists

        # delete button
        button.delete()
        # TODO(ndhandre): For now, we can not guess exact flash message.
        #  Change flash as per BZ-1744478.
        view.flash.assert_success_message('Button:"undefined" was successfully deleted')
        assert not button.exists


@pytest.mark.parametrize('button_group', [True, False],
                         ids=['button_group_with_button', 'single_button'])
def test_generic_objects_with_buttons_ui(appliance, add_generic_object_to_service,
                                         button_group, generic_object_button):
    """
        Tests buttons ui visibility assigned to generic object

        Metadata:
            test_flag: ui

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: GenericObjects
    """
    instance = add_generic_object_to_service
    generic_button = generic_object_button(button_group)
    generic_button_group = generic_button.parent.parent

    with appliance.context.use(ViaUI):
        view = navigate_to(instance, 'MyServiceDetails')
        if button_group:
            assert view.toolbar.group(generic_button_group.name).custom_button.has_item(
                generic_button.name)
        else:
            assert view.toolbar.button(generic_button.name).custom_button.is_displayed
