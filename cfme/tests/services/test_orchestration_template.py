import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.parametrize("template_type", ["CloudFormation", "Heat", "Azure", "VNF", "vApp"],
                         ids=["cnf", "heat", "azure", "vnf", "vapp"], indirect=True),
    #  TODO Unlock VNF once we have VNF provider for testing
    pytest.mark.uncollectif(lambda template_type: template_type == "VNF",
                            reason="VNF requires vCloud provider")
]

# As CFME doesn't verify content of the script - it can be the same for all types
METHOD_TORSO = """
{  "AWSTemplateFormatVersion" : "2010-09-09",
  "Description" : "AWS CloudFormation Sample Template Rails_Single_Instance.",

  "Parameters" : {
    "KeyName": {
      "Description" : "Name of an existing EC2 KeyPair to enable SSH access to the instances",
      "Type": "AWS::EC2::KeyPair::KeyName",
      "ConstraintDescription" : "must be the name of an existing EC2 KeyPair."
    }
  }
}
"""

METHOD_TORSO_copied = """
{

"AWSTemplateFormatVersion" : "2010-09-09",
  "Description" : "AWS CloudFormation Sample Template Rails_Single_Instance.",

  "Parameters" : {
    "KeyName": {
      "Description" : "Name of an existing EC2 KeyPair to enable SSH access to the instances",
      "Type": "AWS::EC2::KeyPair::KeyName",
      "ConstraintDescription" : "must be the name of an existing EC2 KeyPair."
    }
  }
}
"""

# Orchestration template types in tuples (template_name, template_ui_group)
templates = {
    "CloudFormation": ("Amazon CloudFormation", "CloudFormation Templates"),
    "Heat": ("OpenStack Heat", "Heat Templates"),
    "Azure": ("Microsoft Azure", "Azure Templates"),
    "VNF": ("VNF", "VNF Templates"),
    "vApp": ("VMWare vApp", "vApp Templates"),
}


@pytest.fixture(scope="function")
def template_type(request):
    return request.param


@pytest.fixture(scope="function")
def created_template(appliance, template_type):
    method = METHOD_TORSO.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_group=templates.get(template_type)[1],
                                 template_type=templates.get(template_type)[0],
                                 template_name=fauxfactory.gen_alphanumeric(),
                                 description="my template",
                                 content=method)
    yield template
    template.delete()


def test_orchestration_template_crud(appliance, template_type):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    method = METHOD_TORSO.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_group=templates.get(template_type)[1],
                                 template_type=templates.get(template_type)[0],
                                 template_name=fauxfactory.gen_alphanumeric(),
                                 description="my template",
                                 content=method)
    assert template.exists
    with update(template):
        template.description = "my edited description"
    template.delete()
    assert not template.exists


def test_copy_template(created_template):
    """Tests Orchestration template copy

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    copied_method = METHOD_TORSO_copied.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    template = created_template
    template_copy = template.copy_template(f"{template.template_name}_copied",
                                           copied_method)
    assert template_copy.exists
    template_copy.delete()


def test_name_required_error_validation_orch_template(appliance, template_type):
    """Tests error validation if Name wasn't specified during template creation

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    copied_method = METHOD_TORSO_copied.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    collection = appliance.collections.orchestration_templates
    with pytest.raises(AssertionError):
        collection.create(template_group=templates.get(template_type)[1],
                          template_type=templates.get(template_type)[0],
                          template_name=None,
                          description="my template",
                          content=copied_method)


def test_empty_all_fields_error_validation(appliance, template_type):
    """Tests error validation if we try to create template with all empty fields

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    flash_msg = "Error during Orchestration Template creation: new template content cannot be empty"
    collection = appliance.collections.orchestration_templates
    with pytest.raises(Exception, match=flash_msg):
        collection.create(template_group=templates.get(template_type)[1],
                          template_type=templates.get(template_type)[0],
                          template_name=None,
                          description=None,
                          content='')


def test_empty_content_error_validation(appliance, template_type):
    """Tests error validation if content wasn't added during template creation

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    flash_msg = "Error during Orchestration Template creation: new template content cannot be empty"
    collection = appliance.collections.orchestration_templates
    with pytest.raises(AssertionError, match=flash_msg):
        collection.create(template_group=templates.get(template_type)[1],
                          template_type=templates.get(template_type)[0],
                          template_name=fauxfactory.gen_alphanumeric(),
                          description="my template",
                          content='')


@test_requirements.tag
def test_tag_orchestration_template(tag, created_template):
    """Tests template tagging. Verifies that tag was added, confirms in template details,
    removes tag

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """
    navigate_to(created_template, 'Details')
    created_template.add_tag(tag=tag)
    assert ((tag.display_name, tag.category.display_name) in
            [(tags.display_name, tags.category.display_name) for tags in
             created_template.get_tags()])
    created_template.remove_tag(tag=tag)


@pytest.mark.parametrize("action", ["copy", "create"], ids=["copy", "create"])
def test_duplicated_content_error_validation(appliance, created_template, template_type,
                                             action):
    """Tests that we are not allowed to have duplicated content in different templates

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    collection = appliance.collections.orchestration_templates
    if action == "copy":
        copy_name = f"{created_template.template_name}_copied"
        flash_msg = ("Unable to create a new template copy \"{}\": old and new template content "
                     "have to differ.".format(copy_name))
        with pytest.raises(AssertionError, match=flash_msg):
            created_template.copy_template(copy_name, created_template.content)
    elif action == "create":
        with pytest.raises(AssertionError):
            collection.create(template_group=templates.get(template_type)[1],
                              template_type=templates.get(template_type)[0],
                              template_name=fauxfactory.gen_alphanumeric(),
                              description="my template",
                              content=created_template.content)


@pytest.mark.uncollectif(lambda template_type: template_type == "vApp" or template_type == "VNF",
                         reason="vApp requires valid vCloud provider and template for this test")
def test_service_dialog_creation_from_customization_template(request, created_template):
    """Tests Service Dialog creation  from customization template

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    dialog_name = created_template.template_name
    service_dialog = created_template.create_service_dialog_from_template(dialog_name)
    request.addfinalizer(service_dialog.delete_if_exists)
    assert service_dialog.exists
