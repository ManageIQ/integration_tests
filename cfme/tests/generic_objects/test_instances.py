# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import yaml

import cfme.rest.gen_data as rest_gen_data
from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.generic_objects.instance.ui import MyServiceGenericObjectInstanceView
from cfme.services.myservice import MyService
from cfme.tests.automate.custom_button import TextInputDialogView
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.generic_objects]


GEN_OBJ_DIRECTORY = "/var/www/miq/vmdb/tmp/generic_object_definitions"


@pytest.fixture
def gen_obj_def_import_export(appliance):
    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name="rest_gen_class_imp_exp{}".format(fauxfactory.gen_alphanumeric()),
            description="Generic Object Definition",
            attributes={'addr01': 'string'},
            methods=['add_vm', 'remove_vm']
        )
        yield definition
        definition.delete_if_exists()


@pytest.fixture(scope="module")
def categories(request, appliance):
    return rest_gen_data.categories(request, appliance, 3)


@pytest.fixture(scope="module")
def tags(request, appliance, categories):
    return rest_gen_data.tags(request, appliance, categories)


@pytest.fixture
def button_with_dialog(appliance, generic_object, dialog):
    generic_definition = generic_object.definition
    with appliance.context.use(ViaUI):
        button = generic_definition.collections.generic_object_buttons.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            request="call_instance",
            image="ff ff-network-interface",
            dialog=dialog.label
        )

        yield button

        button.delete_if_exists()


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


@pytest.mark.sauce
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
def test_generic_objects_crud(appliance, context, request):
    """
    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        tags: 5.9
        casecomponent: GenericObjects
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name='rest_generic_class{}'.format(fauxfactory.gen_alphanumeric()),
            description='Generic Object Definition',
            attributes={'addr01': 'string'},
            associations={'services': 'Service'}
        )
        assert definition.exists
        request.addfinalizer(definition.delete)

    with appliance.context.use(ViaREST):
        myservices = []
        for _ in range(2):
            service_name = 'rest_service_{}'.format(fauxfactory.gen_alphanumeric())
            rest_service = appliance.rest_api.collections.services.action.create(
                name=service_name,
                display=True
            )
            rest_service = rest_service[0]
            request.addfinalizer(rest_service.action.delete)
            myservices.append(MyService(appliance, name=service_name))
        instance = appliance.collections.generic_objects.create(
            name='rest_generic_instance{}'.format(fauxfactory.gen_alphanumeric()),
            definition=definition,
            attributes={'addr01': 'Test Address'},
            associations={'services': [myservices[0]]}
        )
        request.addfinalizer(instance.delete)
    with appliance.context.use(context):
        if context.name == 'UI':
            # we need to refresh definition page to update instance count,
            # as navigation to instance details happens via this page
            appliance.browser.widgetastic.refresh()
        assert instance.exists

    with appliance.context.use(ViaREST):
        with update(instance):
            instance.attributes = {'addr01': 'Changed'}
            instance.associations = {'services': myservices}
        rest_instance = appliance.rest_api.collections.generic_objects.get(name=instance.name)
        rest_data = appliance.rest_api.get('{}?associations=services'.format(rest_instance.href))
        assert len(rest_data['services']) == 2
        assert rest_data['property_attributes']['addr01'] == 'Changed'
        instance.delete()

    with appliance.context.use(context):
        assert not instance.exists


@pytest.mark.parametrize('button_group', [True, False],
                         ids=['button_group_with_button', 'single_button'])
def test_generic_objects_with_buttons_ui(appliance, request, add_generic_object_to_service,
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


@test_requirements.tag
@pytest.mark.parametrize('tag_place', [True, False], ids=['details', 'collection'])
def test_generic_objects_tag_ui(appliance, generic_object, tag_place):
    """Tests assigning and unassigning tags using UI.

        Metadata:
            test_flag: ui

    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: GenericObjects
    """
    with appliance.context.use(ViaUI):
        assigned_tag = generic_object.add_tag(details=tag_place)
        # TODO uncomment when tags aria added to details
        # tag_available = instance.get_tags()
        # assert any(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not found on the details page'
        generic_object.remove_tag(assigned_tag, details=tag_place)
        # TODO uncomment when tags aria added to details
        # assert not(tag.category.display_name == assigned_tag.category.display_name and
        #            tag.display_name == assigned_tag.display_name
        #            for tag in tag_available), 'Assigned tag was not removed from the details page'


@test_requirements.rest
def test_generic_objects_tag_rest(appliance, generic_object, tags):
    """Tests assigning and unassigning tags using REST.

    Metadata:
        test_flag: rest

    Polarion:
        initialEstimate: 1/4h
        assignee: pvala
        casecomponent: Tagging
        caseimportance: high
    """
    tag = tags[0]
    with appliance.context.use(ViaREST):
        generic_object.add_tag(tag)
        tag_available = generic_object.get_tags()
        assert tag.id in [t.id for t in tag_available], 'Assigned tag was not found'
        generic_object.remove_tag(tag)
        tag_available = generic_object.get_tags()
        assert tag.id not in [t.id for t in tag_available]


@pytest.mark.ignore_stream("5.10")
def test_import_export_generic_object_definition(request, appliance, gen_obj_def_import_export):
    """
    Bugzilla:
        1595259

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.11
        casecomponent: GenericObjects
        testSteps:
            1. Create generic object definition via Rest
            2. Export the generic object definition
            3. Delete the generic object definition
            4. Import the generic object definition
        expectedResults:
            1. The generic object definition should be present in CFME
            2. Yaml file should be present on the appliance with the generic object details
            3. Generic object definition is deleted
            4. Generic object definition once again exists on the appliance
    """
    # Create the generic object directory
    assert appliance.ssh_client.run_command("mkdir {}".format(GEN_OBJ_DIRECTORY)).success

    @request.addfinalizer
    def cleanup():
        assert appliance.ssh_client.run_command("rm -rf {}".format(GEN_OBJ_DIRECTORY)).success

    # Export the user defined generic object definitions
    assert appliance.ssh_client.run_rake_command(
        "evm:export:generic_object_definitions -- --directory {}".format(GEN_OBJ_DIRECTORY)
    ).success
    # Verify the file's information
    try:
        with appliance.ssh_client.open_sftp().open(
                "{}/{}.yaml".format(GEN_OBJ_DIRECTORY, gen_obj_def_import_export.name)
        ) as f:
            data = yaml.safe_load(f)[0]["GenericObjectDefinition"]

    except IOError:
        pytest.fail(
            "IOError: {}/{}.yaml not found on the appliance, "
            "exporting the generic object definition failed".format(
                GEN_OBJ_DIRECTORY, gen_obj_def_import_export.name
            )
        )

    assert data.get("description") == gen_obj_def_import_export.description
    assert data.get("name") == gen_obj_def_import_export.name

    # Delete the generic object definition via the UI
    gen_obj_def_import_export.delete_if_exists()

    # Import the generic object yaml by running the rake command
    assert appliance.ssh_client.run_rake_command(
        "evm:import:generic_object_definitions -- --source {}/{}.yaml".format(
            GEN_OBJ_DIRECTORY,
            gen_obj_def_import_export.name,
        )
    ).success

    assert gen_obj_def_import_export.exists


@pytest.mark.meta(automates=[1729341, 1743266])
def test_generic_object_with_service_button(appliance, generic_object, button_with_dialog):
    """
    Bugzilla:
        1729341
        1743266

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/6h
        caseimportance: high
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: GenericObjects
    """
    # add generic object to service
    myservice = MyService(appliance, name=generic_object.associations.get("services")[0].name)
    with appliance.context.use(ViaREST):
        myservice.add_resource_generic_object(generic_object)
    # now navigate to the details of the generic_object
    view = navigate_to(generic_object, "MyServiceDetails")
    view.toolbar.button(button_with_dialog.name).custom_button.click()
    view = generic_object.create_view(TextInputDialogView, wait=10)
    view.service_name.fill("Custom Button Execute")
    wait_for(lambda: not view.submit.disabled, timeout="10s")
    view.submit.click()

    # now for the actual test, make sure after hitting submit we're on the correct page
    try:
        generic_object.create_view(MyServiceGenericObjectInstanceView, wait=10)
    except TimedOutError:
        pytest.fail("Could not wait for service's generic object view to displayed.")
