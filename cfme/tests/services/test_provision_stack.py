import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.conf import credentials
from cfme.utils.datafile import load_data_file
from cfme.utils.log import logger
from cfme.utils.path import orchestration_path

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([CloudProvider],
                         required_fields=[['provisioning', 'stack_provisioning']],
                         scope="module"),
]


@pytest.fixture
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

        stack_data = {
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
    elif provider.one_of(OpenStackProvider):
        stack_prov = provisioning['stack_provisioning']
        stack_data = {
            'stack_name': stackname,
            'key': stack_prov['key_name'],
            'flavor': stack_prov['instance_type'],
        }
    else:
        stack_prov = provisioning['stack_provisioning']
        if appliance.version < '5.9':
            stack_data = {
                'stack_name': stackname,
                'stack_timeout': stack_timeout,
                'virtualMachineName': vm_name,
                'KeyName': stack_prov['key_name'],
                'InstanceType': stack_prov['instance_type'],
                'SSHLocation': provisioning['ssh_location']
            }
        else:
            stack_data = {
                'stack_name': stackname,
                'stack_timeout': stack_timeout,
                'param_virtualMachineName': vm_name,
                'param_KeyName': stack_prov['key_name']
            }
    return stack_data


@pytest.fixture
def dialog_name():
    return 'dialog_{}'.format(fauxfactory.gen_alphanumeric())


@pytest.yield_fixture
def template(provider, provisioning, dialog_name, stack):
    template_type = provisioning['stack_provisioning']['template_type']
    template_name = fauxfactory.gen_alphanumeric()
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=template_name)
    file = provisioning['stack_provisioning']['data_file']
    data_file = load_data_file(str(orchestration_path.join(file)))
    template.create(data_file.read().replace('CFMETemplateName', template_name))
    template.create_service_dialog_from_template(dialog_name, template.template_name)
    yield template
    if stack.exists:
        stack.retire_stack()
    if template.exists:
        template.delete()


@pytest.yield_fixture
def catalog():
    cat_name = "cat_{}".format(fauxfactory.gen_alphanumeric())
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog
    if catalog.exists:
        catalog.delete()


@pytest.yield_fixture
def catalog_item(dialog, catalog, template, provider, dialog_name):
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
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture
def order_service(appliance, catalog_item, stack_data):
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name, stack_data)
    service_catalogs.order()


@pytest.yield_fixture
def provision_request(appliance, catalog_item, order_service):
    provision_request = appliance.collections.requests.instantiate(catalog_item.name,
                                                                   partial_check=True)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    provision_request.wait_for_request(method='ui')
    yield provision_request
    if provision_request.exists:
        provision_request.remove_request()


@pytest.yield_fixture
def service(appliance, provision_request):
    last_message = provision_request.get_request_row_from_ui()['Last Message'].text
    service_name = last_message.split()[2].strip('[]')
    service = MyService(appliance, service_name)
    yield service
    if service.exists:
        service.delete()


@pytest.fixture
def stack(appliance, provider, stack_data):
    return appliance.collections.stacks.instantiate(stack_data['stack_name'], provider=provider)


def test_provision_stack(provision_request, stack):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    assert provision_request.is_succeeded()
    stack.wait_for_exists()


def test_reconfigure_service(service, provision_request):
    """Tests service reconfiguring

    Metadata:
        test_flag: provision
    """
    assert provision_request.is_succeeded()
    service.reconfigure_service()


def test_remove_template_provisioning(appliance, catalog_item, template, order_service, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    # This is part of test - remove template and see if provision fails, so not added as finalizer
    template.delete()
    request_description = 'Provisioning Service [{}] from [{}]'.format(catalog_item.name,
                                                                       catalog_item.name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')

    @request.addfinalizer
    def _finalize():
        last_message = provision_request.get_request_row_from_ui()['Last Message'].text
        service_name = last_message.split()[2].strip('[]')
        myservice = MyService(appliance, service_name)
        if myservice.exists:
            myservice.delete

    assert (provision_request.row.last_message.text == 'Service_Template_Provisioning failed' or
            provision_request.row.status.text == "Error")


def test_retire_stack(appliance, provider, provision_request, stack):
    """Tests stack retirement

    Metadata:
        test_flag: provision
    """
    assert provision_request.is_succeeded()
    stack.wait_for_exists()
    stack.retire_stack()
