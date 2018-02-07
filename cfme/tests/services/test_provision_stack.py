import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.stack import StackCollection
from cfme.configure.settings import DefaultView
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.conf import credentials
from cfme.utils.datafile import load_data_file
from cfme.utils.log import logger
from cfme.utils.path import orchestration_path
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.provider([CloudProvider],
                         required_fields=[['provisioning', 'stack_provisioning']],
                         scope="module"),
]


@pytest.fixture(scope="function")
def template(provider, provisioning, setup_provider):
    template_type = provisioning['stack_provisioning']['template_type']
    template_name = fauxfactory.gen_alphanumeric()
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=template_name)

    file = provisioning['stack_provisioning']['data_file']
    data_file = load_data_file(str(orchestration_path.join(file)))

    template.create(data_file.read().replace('CFMETemplateName', template_name))
    dialog_name = "dialog_" + fauxfactory.gen_alphanumeric()
    template.create_service_dialog_from_template(dialog_name, template.template_name)
    yield template, dialog_name
    template.delete()


@pytest.fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog
    catalog.delete()


@pytest.fixture(scope="function")
def catalog_item(dialog, catalog, template, provider):
    template, dialog = template
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration",
                               name=item_name,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=dialog,
                               orch_template=template,
                               provider=provider)
    catalog_item.create()
    yield catalog_item, template
    catalog_item.delete()


def random_desc():
    return fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="function")
def stack_data(appliance, provider, provisioning):
    random_base = fauxfactory.gen_alphanumeric()
    stackname = 'test{}'.format(random_base)
    vm_name = 'test-{}'.format(random_base)
    stack_timeout = "20"
    if provider.one_of(AzureProvider):
        try:
            template = provider.data.templates.small_template
            vm_user = credentials[template.creds].username
            vm_password = credentials[template.creds].password
        except AttributeError:
            pytest.skip('Could not find small_template or credentials for {}'.format(provider.name))

        _stack_data = {
            'stack_name': stackname,
            'resource_group': provisioning.get('resource_group'),
            'deploy_mode': provisioning.get('mode'),
            'location': provisioning.get('region_api'),
            'vmname': vm_name,
            'vmuser': vm_user,
            'vmpassword': vm_password,
            'vmsize': provisioning.get('vm_size'),
            'cloudnetwork': provisioning.get('cloud_network').split()[0],
            'cloudsubnet': provisioning.get('cloud_subnet').split()[0]
        }
    elif provider.type == 'openstack':
        stack_prov = provisioning['stack_provisioning']

        _stack_data = {
            'stack_name': stackname,
            'key': stack_prov['key_name'],
            'flavor': stack_prov['instance_type'],
        }
    else:
        stack_prov = provisioning['stack_provisioning']
        if appliance.version < '5.9':
            _stack_data = {
                'stack_name': stackname,
                'stack_timeout': stack_timeout,
                'vm_name': vm_name,
                'key_name': stack_prov['key_name'],
                'select_instance_type': stack_prov['instance_type'],
                'ssh_location': provisioning['ssh_location']
            }
        else:
            _stack_data = {
                'stack_name': stackname,
                'stack_timeout': stack_timeout,
                'param_virtualMachineName': vm_name,
                'param_KeyName': stack_prov['key_name']
            }
    return _stack_data


def test_provision_stack(appliance, setup_provider, provider, provisioning, catalog, catalog_item,
                         request, stack_data):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, template = catalog_item

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()


def test_reconfigure_service(appliance, provider, provisioning, catalog, catalog_item, request,
                             stack_data):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, template = catalog_item

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded()
    last_message = provision_request.get_request_row_from_ui()['Last Message'].text
    service_name = last_message.split()[2].strip('[]')
    myservice = MyService(appliance, service_name)
    myservice.reconfigure_service()


def test_remove_template_provisioning(appliance, provider, provisioning, catalog, catalog_item,
                                      stack_data):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, template = catalog_item
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name, stack_data)
    service_catalogs.order()
    # This is part of test - remove template and see if provision fails , so not added as finalizer
    template.delete()
    request_description = 'Provisioning Service [{}] from [{}]'.format(catalog_item.name,
                                                                       catalog_item.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert (provision_request.row.last_message.text == 'Service_Template_Provisioning failed' or
            provision_request.row.status.text == "Error")


def test_retire_stack(appliance, provider, provisioning, catalog, catalog_item, request,
                      stack_data):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, template = catalog_item
    DefaultView.set_default_view("Stacks", "Grid View")

    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_succeeded()
    stack = StackCollection(appliance).instantiate(stack_data['stack_name'], provider=provider)
    stack.wait_for_exists()
    stack.retire_stack()

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)


def clean_up(stack_data, provider):
    try:
        logger.info("Removing Stack and it's VM")
        # stack_exist returns 400 if stack ID not found, which triggers an exception
        if provider.mgmt.stack_exist(stack_data['stack_name']):
            wait_for(lambda: provider.mgmt.delete_stack(stack_data['stack_name']),
                     delay=10, num_sec=800, message="wait for stack delete")
        if provider.type == 'azure' and provider.mgmt.does_vm_exist(stack_data['vmname']):

            wait_for(lambda: provider.mgmt.delete_vm(stack_data['vmname']),
                     delay=10, num_sec=800, message="wait for vm delete")
    except Exception as ex:
        logger.warning('Exception while checking/deleting stack, continuing: {}'
                       .format(ex.message))
        pass
