# -*- coding: utf-8 -*-
import fauxfactory
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
import pytest
from utils import testgen
from utils.update import update


pytestmark = [pytest.mark.usefixtures("logged_in"),
              pytest.mark.ignore_stream("5.3")]

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
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'provisioning')
    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        # required keys should be a subset of the dict keys set
        if not {'stack_provisioning'}.issubset(args['provisioning'].viewkeys()):
            # Need image for image -> instance provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append([args[argname] for argname in argnames])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def test_orchestration_template_crud(provisioning):
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric(),
                                     description="my template")
    template.create(METHOD_TORSO)
    with update(template):
        template.description = "my edited description"
    template.delete()


@pytest.mark.meta(blockers=[1271723])
def test_copy_template(provisioning):
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric(),
                                     description="my template")
    template.create(METHOD_TORSO)
    template.copy_template(template.template_name + "_copied", METHOD_TORSO_copied)
    template.delete()
