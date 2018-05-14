import fauxfactory
import pytest
from widgetastic_patternfly import DropdownItemDisabled

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.datafile import load_data_file
from cfme.utils.path import orchestration_path

pytestmark = [
    pytest.mark.meta(server_roles='+automate'),
    pytest.mark.ignore_stream('upstream'),
    test_requirements.stack,
    pytest.mark.tier(2),
    pytest.mark.usefixtures("setup_provider_modscope"),
    pytest.mark.provider([CloudProvider],
                         required_fields=[['provisioning', 'stack_provisioning']],
                         scope='module'),
]


@pytest.fixture
def stack_data(appliance, provider, provisioning):
    random_base = fauxfactory.gen_alphanumeric()
    stackname = 'test{}'.format(random_base)
    vm_name = 'test-{}'.format(random_base)
    stack_timeout = '20'
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


@pytest.fixture
def template(appliance, provider, provisioning, dialog_name, stack):
    template_group = provisioning['stack_provisioning']['template_type']
    template_type = provisioning['stack_provisioning']['template_type_dd']
    template_name = fauxfactory.gen_alphanumeric()
    file = provisioning['stack_provisioning']['data_file']
    data_file = load_data_file(str(orchestration_path.join(file)))
    content = data_file.read().replace('CFMETemplateName', template_name)
    collection = appliance.collections.orchestration_templates
    template = collection.create(template_group=template_group, template_name=template_name,
                                 template_type=template_type, description="my template",
                                 content=content)
    template.create_service_dialog_from_template(dialog_name)
    yield template
    if stack.exists:
        stack.retire_stack()
    if template.exists:
        template.delete()


@pytest.fixture
def catalog(appliance):
    cat_name = "cat_{}".format(fauxfactory.gen_alphanumeric())
    catalog = appliance.collections.catalogs.create(name=cat_name, description="my catalog")
    yield catalog
    if catalog.exists:
        catalog.delete()


@pytest.fixture
def catalog_item(appliance, dialog, catalog, template, provider, dialog_name):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ORCHESTRATION,
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog_name,
        orch_template=template,
        provider_name=provider.name,
    )
    yield catalog_item
    if catalog_item.exists:
        catalog_item.delete()


@pytest.fixture
def service_catalogs(appliance, catalog_item, stack_data):
    return ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name, stack_data)


@pytest.fixture
def stack(appliance, provider, stack_data):
    return appliance.collections.stacks.instantiate(stack_data['stack_name'], provider=provider)


@pytest.fixture
def order_stack(appliance, request, service_catalogs, stack):
    """Fixture which prepares provisioned stack"""
    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(lambda: _cleanup(appliance, provision_request))
    assert provision_request.is_succeeded()
    stack.wait_for_exists()
    return provision_request, stack


def _cleanup(appliance=None, provision_request=None, service=None):
    if not service:
        last_message = provision_request.get_request_row_from_ui()['Last Message'].text
        service_name = last_message.split()[2].strip('[]')
        myservice = MyService(appliance, service_name)
    else:
        myservice = service
    if myservice.exists:
        myservice.delete()


def test_provision_stack(order_stack):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    provision_request, stack = order_stack
    assert provision_request.is_succeeded()


@pytest.mark.uncollectif(lambda: BZ(1575935, forced_streams=['5.8', '5.9']).blocks,
                         reason='impossible to reconfigure orchestration service due to BZ 1575935')
def test_reconfigure_service(appliance, service_catalogs, request):
    """Tests service reconfiguring

    Metadata:
        test_flag: provision
    """
    provision_request = service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    last_message = provision_request.get_request_row_from_ui()['Last Message'].text
    service_name = last_message.split()[2].strip('[]')
    myservice = MyService(appliance, service_name)
    request.addfinalizer(lambda: _cleanup(service=myservice))
    assert provision_request.is_succeeded()
    myservice.reconfigure_service()


@pytest.mark.uncollectif(lambda provider: provider.one_of(EC2Provider),
                         reason='EC2 locks template between Stack order and template removal')
def test_remove_non_read_only_orch_template(appliance, provider, template, service_catalogs,
                                            request):
    """
    Steps:
    1. Order Service which uses Orchestration template
    2. Try to remove this Orchestration template

    Metadata:
        test_flag: provision
    """
    provision_request = service_catalogs.order()
    request.addfinalizer(lambda: _cleanup(appliance, provision_request))
    template.delete()
    assert (provision_request.rest.message == 'Service_Template_Provisioning failed' or
            provision_request.status == 'Error')
    assert not template.exists


@pytest.mark.uncollectif(lambda provider: not provider.one_of(EC2Provider),
                         reason='Only EC2 locks orchestration template')
def test_remove_read_only_orch_template_neg(appliance, provider, template, service_catalogs,
                                            request):
    """
    For RHOS/Azure the original template will remain stand-alone while the stack links
    to a new template read from the RHOS/Azure provider. Hence we can delete used orchestration
    template for RHOS/Azure.

    Steps:
    1. Order Service which uses Orchestration template
    2. Try to remove this Orchestration template

    Metadata:
        test_flag: provision
    """
    provision_request = service_catalogs.order()
    request.addfinalizer(lambda: _cleanup(appliance, provision_request))
    provision_request.wait_for_request(method='ui')
    with pytest.raises(DropdownItemDisabled):
        template.delete()


def test_retire_stack(order_stack):
    """Tests stack retirement.

    Steps:
    1. Retire Orchestration stack
    2. Verify it doesn't exist in UI

    Metadata:
        test_flag: provision
    """
    _, stack = order_stack
    stack.retire_stack()
    assert not stack.exists, "Stack still visible in UI"
