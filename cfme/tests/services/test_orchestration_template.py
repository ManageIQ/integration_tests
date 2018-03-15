# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.utils import error
from cfme.utils.update import update
from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.provider([CloudProvider],
                         required_fields=[['provisioning', 'stack_provisioning']],
                         scope="module")
]


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


@pytest.fixture(scope="function")
def create_template():
    method = METHOD_TORSO.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    return method


def test_orchestration_template_crud(appliance, provisioning, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_type=template_type, temp_type=temp_type,
                                 template_name=fauxfactory.gen_alphanumeric(),
                                 description="my template", content=create_template)

    with update(template):
        template.description = "my edited description"
    template.delete()


def test_copy_template(appliance, provisioning, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_type=template_type, temp_type=temp_type,
                                 template_name=fauxfactory.gen_alphanumeric(),
                                 description="my template", content=create_template)
    copied_method = METHOD_TORSO_copied.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    template.copy_template(template.template_name + "_copied", copied_method)
    template.delete()


def test_name_required_error_validation(appliance, provisioning, create_template):
    flash_msg = \
        "Error during 'Orchestration Template creation': Validation failed: Name can't be blank"
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    with error.expected(flash_msg):
        collection.create(template_type=template_type, template_name=None,
                          temp_type=temp_type, description="my template",
                          content=create_template)


def test_all_fields_required_error_validation(appliance, provisioning, create_template):
    flash_msg = \
        "Error during 'Orchestration Template creation': Validation failed: Name can't be blank"
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    with error.expected(flash_msg):
        collection.create(template_type=template_type, template_name=None,
                          temp_type=temp_type, description=None,
                          content=create_template)


def test_new_template_required_error_validation(appliance, provisioning):
    flash_msg = \
        'Error during Orchestration Template creation: new template content cannot be empty'
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    with error.expected(flash_msg):
        collection.create(template_type=template_type, temp_type=temp_type,
                          template_name=fauxfactory.gen_alphanumeric(),
                          description="my template", content='')


def test_tag_orchestration_template(appliance, provisioning, tag, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    temp_type = provisioning['stack_provisioning']['template_type_dd']
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_type=template_type, temp_type=temp_type,
                                 template_name=fauxfactory.gen_alphanumeric(),
                                 description="my template", content=create_template)
    navigate_to(template, 'Details')
    template.add_tag(tag=tag)
    template.remove_tag(tag=tag)
    template.delete()
