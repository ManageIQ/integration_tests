import fauxfactory
import pytest
import yaml

from cfme import test_requirements
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance import ViaREST
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [test_requirements.generic_objects]

GEN_OBJ_DIRECTORY = "/var/www/miq/vmdb/tmp/generic_object_definitions"


@pytest.fixture
def gen_obj_def_import_export(appliance):
    with appliance.context.use(ViaREST):
        definition = appliance.collections.generic_object_definitions.create(
            name=fauxfactory.gen_alphanumeric(28, start="rest_gen_class_imp_exp_"),
            description="Generic Object Definition",
            attributes={'addr01': 'string'},
            methods=['add_vm', 'remove_vm']
        )
        yield definition
        definition.delete_if_exists()


@pytest.mark.sauce
@pytest.mark.tier(0)
@pytest.mark.parametrize('context', [ViaREST, ViaUI])
def test_generic_object_definition_crud(appliance, context, soft_assert):
    """
    Polarion:
        assignee: tpapaioa
        casecomponent: GenericObjects
        caseimportance: high
        initialEstimate: 1/12h
        tags: 5.9
    """
    with appliance.context.use(context):
        definition = appliance.collections.generic_object_definitions.create(
            name=f"{context.name.lower()}_generic_class{fauxfactory.gen_alphanumeric()}",
            description="Generic Object Definition",
            attributes={"addr01": "string"},
            associations={"services": "Service"},
            methods=["hello_world"])
        if context.name == 'UI':
            view = appliance.browser.create_view(BaseLoggedInPage)
            view.flash.assert_success_message(
                f'Generic Object Class "{definition.name}" has been successfully added.')
        assert definition.exists

        with update(definition):
            definition.name = f'{definition.name}_updated'
            definition.attributes = {"new_address": "string"}
        if context.name == 'UI':
            view.flash.assert_success_message(
                f'Generic Object Class "{definition.name}" has been successfully saved.')
            view = navigate_to(definition, 'Details')
            soft_assert(view.summary('Attributes (2)').get_text_of('new_address'))
            soft_assert(view.summary('Attributes (2)').get_text_of('addr01'))
            soft_assert(view.summary('Associations (1)').get_text_of('services'))
        else:
            rest_definition = appliance.rest_api.collections.generic_object_definitions.get(
                name=definition.name)
            soft_assert("new_address" in rest_definition.properties['attributes'])
            soft_assert("addr01" not in rest_definition.properties['attributes'])

        definition.delete()
        if context.name == 'UI' and not BZ(bug_id=1644658, forced_streams=["5.10"]).blocks:
            view.flash.assert_success_message(
                f'Generic Object Class:"{definition.name}" was successfully deleted')
        assert not definition.exists


@pytest.mark.manual('manualonly')
@pytest.mark.tier(3)
def test_generic_objects_class_accordion_should_display_when_locale_is_french():
    """ Generic objects class accordion should display when locale is french
    Polarion:
        assignee: tpapaioa
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/6h
        startsin: 5.10
        tags: service
    Bugzilla:
        1594480
    """
    pass


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(blockers=[BZ(1650104)])
def test_upload_image_generic_object_definition(appliance):
    """
    Bugzilla:
        1650104

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/30h
        caseimportance: medium
        caseposneg: negative
        testtype: functional
        startsin: 5.11
        casecomponent: GenericObjects
    """
    view = navigate_to(appliance.collections.generic_object_definitions, "Add")
    view.custom_image_file.upload_chosen_file.click()
    # make sure the flash assertion appears
    view.flash.assert_message("No file chosen.")
    # click button again
    view.custom_image_file.upload_chosen_file.click()
    # make sure only a single message is present
    assert len(view.flash.read()) == 1
    view.cancel.click()


@pytest.mark.ignore_stream("5.10")
def test_import_export_generic_object_definition(request, appliance, gen_obj_def_import_export):
    """
    Bugzilla:
        1595259

    Polarion:
        assignee: tpapaioa
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
    assert appliance.ssh_client.run_command(f"mkdir {GEN_OBJ_DIRECTORY}").success

    @request.addfinalizer
    def cleanup():
        assert appliance.ssh_client.run_command(f"rm -rf {GEN_OBJ_DIRECTORY}").success

    # Export the user defined generic object definitions
    assert appliance.ssh_client.run_rake_command(
        f"evm:export:generic_object_definitions -- --directory {GEN_OBJ_DIRECTORY}"
    ).success
    # Verify the file's information
    try:
        with appliance.ssh_client.open_sftp().open(
                f"{GEN_OBJ_DIRECTORY}/{gen_obj_def_import_export.name}.yaml"
        ) as f:
            data = yaml.safe_load(f)[0]["GenericObjectDefinition"]

    except OSError:
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
