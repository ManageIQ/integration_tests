import pytest
import fauxfactory

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.myservice import MyService
from cfme.services import requests
from cfme.web_ui import flash
from utils import testgen
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("5.2", "5.3", "upstream")
]

METHOD_TORSO = """
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


@pytest.fixture(scope="function")
def dialog(provisioning):
    dialog_name = "dialog_" + fauxfactory.gen_alphanumeric()
    template_type = provisioning['stack_provisioning']['template_type']
    orch_dialog = OrchestrationTemplate(template_type=template_type)
    template_name = orch_dialog.create_service_dialog(dialog_name)
    return dialog_name, template_name


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog
    catalog.delete()


def test_provision_stack(setup_provider, provider, provisioning, dialog, catalog, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    dialog_name, template_name = dialog
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog_name, orch_template=template_name,
                  provider_type=provider.name)
    catalog_item.create()
    stackname = "test-" + fauxfactory.gen_alphanumeric()
    if provider.type == 'ec2':
        stack_data = {
            'stack_name': stackname,
            'key_name': provisioning['stack_provisioning']['key_name'],
            'db_user': provisioning['stack_provisioning']['db_user'],
            'db_password': provisioning['stack_provisioning']['db_password'],
            'db_root_password': provisioning['stack_provisioning']['db_root_password'],
            'select_instance_type': provisioning['stack_provisioning']['instance_type'],
        }
    elif provider.type == 'openstack':
        stack_data = {
            'stack_name': stackname,
        }

    @request.addfinalizer
    def _cleanup_vms():
        if provider.mgmt.stack_exist(stackname):
            provider.mgmt.delete_stack(stackname)

    service_catalogs = ServiceCatalogs("service_name", stack_data)
    service_catalogs.order_stack_item(catalog.name, catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2500, delay=20)
    assert row.last_message.text == 'Service Provisioned Successfully'


@pytest.mark.meta(blockers=[1221333])
def test_reconfigure_service(setup_provider, provider, provisioning, dialog, catalog, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    dialog_name, template_name = dialog
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog_name, orch_template=template_name,
                  provider_type=provider.name)
    catalog_item.create()
    if provider.type == 'ec2':
        stack_data = {
            'stack_name': fauxfactory.gen_alphanumeric(),
            'key_name': provisioning['stack_provisioning']['key_name'],
            'db_user': provisioning['stack_provisioning']['db_user'],
            'db_password': provisioning['stack_provisioning']['db_password'],
            'db_root_password': provisioning['stack_provisioning']['db_root_password'],
            'select_instance_type': provisioning['stack_provisioning']['instance_type'],
        }
    elif provider.type == 'openstack':
        stack_data = {
            'stack_name': fauxfactory.gen_alphanumeric()
        }
    service_catalogs = ServiceCatalogs("service_name", stack_data)
    service_catalogs.order_stack_item(catalog.name, catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2000, delay=20)
    assert row.last_message.text == 'Service Provisioned Successfully'
    myservice = MyService(catalog_item.name)
    myservice.reconfigure_service()


@pytest.mark.meta(blockers=[1236932])
def test_remove_template_provisioning(setup_provider, provider, provisioning, catalog, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    dialog_name_new = "dialog_" + fauxfactory.gen_alphanumeric()
    template_type = provisioning['stack_provisioning']['template_type']
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=fauxfactory.gen_alphanumeric())
    template.create(METHOD_TORSO)
    template.create_service_dialog_from_template(dialog_name_new, template.template_name)

    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog_name_new, orch_template=template.template_name,
                  provider_type=provider.name)
    catalog_item.create()
    if provider.type == 'ec2':
        stack_data = {
            'stack_name': "stack" + fauxfactory.gen_alphanumeric()
        }
    elif provider.type == 'openstack':
        stack_data = {
            'stack_name': "stack" + fauxfactory.gen_alphanumeric()
        }
    service_catalogs = ServiceCatalogs("service_name", stack_data)
    service_catalogs.order_stack_item(catalog.name, catalog_item)
    flash.assert_no_errors()
    template.delete()
    row_description = 'Provisioning Service [{}] from [{}]'.format(item_name, item_name)
    cells = {'Description': row_description}
    wait_for(lambda: requests.go_to_request(cells), num_sec=500, delay=20)
    row, __ = wait_for(requests.wait_for_request, [cells, True],
      fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Service_Template_Provisioning failed'
