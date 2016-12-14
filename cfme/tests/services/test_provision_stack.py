import pytest
import fauxfactory

from cfme.configure.settings import DefaultView
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.services import requests
from cfme.cloud.provider import CloudProvider
from cfme.cloud.stack import Stack
from cfme import test_requirements
from utils import testgen, version
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.tier(2)
]

AWS_TEMPLATE = """
{
  "AWSTemplateFormatVersion" : "2010-09-09",
  "Description" : "AWS CloudFormation Sample Template DynamoDB_Table",
  "Parameters" : {
    "HaskKeyElementName" : {
      "Description" : "HashType PrimaryKey Name",
      "Type" : "String",
      "AllowedPattern" : "[a-zA-Z0-9]*",
      "Default" : "SSS",
      "MinLength": "1",
      "MaxLength": "2048",
      "ConstraintDescription" : "must contain only alphanumberic characters"
    },

    "HaskKeyElementType" : {
      "Description" : "HashType PrimaryKey Type",
      "Type" : "String",
      "Default" : "S",
      "AllowedPattern" : "[S|N]",
      "MinLength": "1",
      "MaxLength": "1",
      "ConstraintDescription" : "must be either S or N"
    },

    "ReadCapacityUnits" : {
      "Description" : "Provisioned read throughput",
      "Type" : "Number",
      "Default" : "5",
      "MinValue": "5",
      "MaxValue": "10000",
      "ConstraintDescription" : "must be between 5 and 10000"
    },

    "WriteCapacityUnits" : {
      "Description" : "Provisioned write throughput",
      "Type" : "Number",
      "Default" : "10",
      "MinValue": "5",
      "MaxValue": "10000",
      "ConstraintDescription" : "must be between 5 and 10000"
    }
  },
  "Resources" : {
    "myDynamoDBTable" : {
      "Type" : "AWS::DynamoDB::Table",
      "Properties" : {
        "AttributeDefinitions": [ {
          "AttributeName" : {"Ref" : "HaskKeyElementName"},
          "AttributeType" : {"Ref" : "HaskKeyElementType"}
        } ],
        "KeySchema": [
          { "AttributeName": {"Ref" : "HaskKeyElementName"}, "KeyType": "HASH" }
        ],
        "ProvisionedThroughput" : {
          "ReadCapacityUnits" : {"Ref" : "ReadCapacityUnits"},
          "WriteCapacityUnits" : {"Ref" : "WriteCapacityUnits"}
        }
      }
    }
  },
  "Outputs" : {
    "TableName" : {
      "Value" : {"Ref" : "myDynamoDBTable"},
      "Description" : "Table name of the newly created DynamoDB table"
    }
  }
}
"""

HEAT_TEMPLATE = """
heat_template_version: 2013-05-23
description: Simple template to deploy a single compute instance
parameters:
  image:
    type: string
    label: Image name or ID
    description: Image to be used for compute instance
    default: cirros
  flavor:
    type: string
    label: Flavor
    description: Type of instance (flavor) to be used
    default: m1.small
  key:
    type: string
    label: Key name
    description: Name of key-pair to be used for compute instance
    default: psav
  private_network:
    type: string
    label: Private network name or ID
    description: Network to attach instance to.
    default: c0f0db9c-846f-4d4e-b058-0db5bfb2cb90
resources:
  my_instance:
    type: OS::Nova::Server
    properties:
      image: { get_param: image }
      flavor: { get_param: flavor }
      key_name: { get_param: key }
      networks:
        - uuid: { get_param: private_network }
outputs:
  instance_ip:
    description: IP address of the instance
    value: { get_attr: [my_instance, first_address]}
"""


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[
        ['provisioning', 'stack_provisioning']
    ],
    scope="module")


@pytest.yield_fixture(scope="function")
def template(provider, provisioning, dialog_name):
    template_type = provisioning['stack_provisioning']['template_type']
    if provider.type == 'azure':
        template_name = 'azure-single-vm-from-user-image'
    else:
        template_name = fauxfactory.gen_alphanumeric()

    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=template_name)

    if provider.type == "ec2":
        method = AWS_TEMPLATE.replace('CloudFormation', random_desc())
    elif provider.type == "openstack":
        method = HEAT_TEMPLATE.replace('Simple', random_desc())

    template.create(method)

    if provider.type != "azure":
        template.create_service_dialog_from_template(dialog_name, template.template_name)

    yield template


@pytest.yield_fixture(scope="function")
def dialog_name(provider):
    if provider.type == "azure":
        dialog_name = "azure-single-vm-from-user-image"
    else:
        dialog_name = "dialog_" + fauxfactory.gen_alphanumeric()
    yield dialog_name


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(dialog_name, catalog, template, provider):
    item_name = fauxfactory.gen_alphanumeric()

    catalog_item = CatalogItem(item_type="Orchestration",
                               name=item_name,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=dialog_name,
                               orch_template=template,
                               provider=provider)
    catalog_item.create()

    yield catalog_item, item_name


def random_desc():
    return fauxfactory.gen_alphanumeric()


def prepare_stack_data(provider, provisioning):
    stackname = "test" + fauxfactory.gen_alphanumeric()
    if provider.type == "azure":
        vm_name = "test" + fauxfactory.gen_alphanumeric()
        vm_user, vm_password, vm_size, resource_group,\
            user_image, os_type, mode = map(provisioning.get,
         ('vm_user', 'vm_password', 'vm_size', 'resource_group',
        'user_image', 'os_type', 'mode'))

        stack_data = {
            'stack_name': stackname,
            'vm_name': vm_name,
            'resource_group': resource_group,
            'mode': mode,
            'vm_user': vm_user,
            'vm_password': vm_password,
            'vm_size': vm_size
        }
        return stack_data
    else:
        stack_data = {'stack_name': stackname}
        return stack_data


def test_provision_stack(setup_provider, provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)

    @request.addfinalizer
    def _cleanup_vms():
        try:
            # stack_exist returns 400 if stack ID not found, which triggers an exception
            if provider.mgmt.stack_exist(stack_data['stack_name']):
                wait_for(lambda: provider.mgmt.delete_stack(stack_data['stack_name']),
                         delay=10, num_sec=800, message="wait for stack delete")
            stack_data['vm_name'].delete_from_provider()
            catalog_item.orch_template.delete()
        except Exception as ex:
            logger.warning('Exception while checking/deleting stack, continuing: {}'
                           .format(ex.message))
            pass

    service_catalogs = ServiceCatalogs(item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2500, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text


@pytest.mark.uncollectif(lambda: version.current_version() <= '5.5')
def test_reconfigure_service(provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)

    @request.addfinalizer
    def _cleanup_vms():
        try:
            if provider.mgmt.stack_exist(stack_data['stack_name']):
                wait_for(lambda: provider.mgmt.delete_stack(stack_data['stack_name']),
                 delay=10, num_sec=800, message="wait for stack delete")
            stack_data['vm_name'].delete_from_provider()
            catalog_item.orch_template.delete()
        except Exception as ex:
            logger.warning('Exception while checking/deleting stack, continuing: {}'
                           .format(ex.message))
            pass

    service_catalogs = ServiceCatalogs(item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2000, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text

    myservice = MyService(catalog_item.name)
    myservice.reconfigure_service()


def test_remove_template_provisioning(provider, provisioning, catalog, catalog_item, template):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)
    service_catalogs = ServiceCatalogs(item_name, stack_data)
    service_catalogs.order()
    # This is part of test - remove template and see if provision fails , so not added as finalizer
    template.delete()
    row_description = 'Provisioning Service [{}] from [{}]'.format(item_name, item_name)
    cells = {'Description': row_description}
    wait_for(lambda: requests.find_request(cells), num_sec=500, delay=20)
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Service_Template_Provisioning failed'


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
def test_retire_stack(provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    DefaultView.set_default_view("Stacks", "Grid View")

    stack_data = prepare_stack_data(provider, provisioning)
    service_catalogs = ServiceCatalogs(item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2500, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text

    stack = Stack(stack_data['stack_name'])
    stack.wait_for_appear()
    stack.retire_stack()

    @request.addfinalizer
    def _cleanup_templates():
        try:
            stack_data['vm_name'].delete_from_provider()
            catalog_item.orch_template.delete()
        except Exception as ex:
            logger.warning('Exception while checking/deleting stack, continuing: {}'
                           .format(ex.message))
            pass
