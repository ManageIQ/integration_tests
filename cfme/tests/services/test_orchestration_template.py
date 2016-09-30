# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from utils import testgen, error
from utils.update import update
from cfme.web_ui import mixins
from cfme.fixtures import pytest_selenium as sel
from cfme import test_requirements


pytestmark = [test_requirements.stack, pytest.mark.tier(2)]

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


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, required_fields=[
        ['provisioning', 'stack_provisioning']
    ])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.yield_fixture(scope="function")
def create_template():
    method = METHOD_TORSO.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    yield method


def test_orchestration_template_crud(provisioning, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric(),
                                     description="my template")
    template.create(create_template)
    with update(template):
        template.description = "my edited description"
    template.delete()


def test_copy_template(provisioning, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric(),
                                     description="my template")
    template.create(create_template)
    copied_method = METHOD_TORSO_copied.replace('CloudFormation', fauxfactory.gen_alphanumeric())
    template.copy_template(template.template_name + "_copied", copied_method)
    template.delete()


def test_name_required_error_validation(provisioning, create_template):
    flash_msg = \
        "Error during 'Orchestration Template creation': Validation failed: Name can't be blank"
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=None,
                                     description="my template")
    with error.expected(flash_msg):
        template.create(create_template)


def test_all_fields_required_error_validation(provisioning, create_template):
    flash_msg = \
        "Error during 'Orchestration Template creation': Validation failed: Name can't be blank"
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=None,
                                     description=None)

    with error.expected(flash_msg):
        template.create(create_template)


def test_new_template_required_error_validation(provisioning):
    flash_msg = \
        'Error during Orchestration Template creation: new template content cannot be empty'
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric(),
                                     description="my template")

    with error.expected(flash_msg):
        template.create('')


def test_tag_orchestration_template(provisioning, tag, create_template):
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                    template_name=fauxfactory.gen_alphanumeric(),
                                    description="my template")
    template.create(create_template)
    sel.force_navigate('select_template', context={
        'template_type': template.template_type,
        'template_name': template.template_name})
    mixins.add_tag(tag)
    mixins.remove_tag(tag)
    template.delete()
