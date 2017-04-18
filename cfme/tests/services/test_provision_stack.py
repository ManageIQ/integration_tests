import pytest
import fauxfactory

from cfme.configure.settings import DefaultView
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.orchestration_template import OrchestrationTemplate
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.myservice import MyService
from cfme.services import requests
from cfme.cloud.provider import CloudProvider
from cfme.cloud.stack import Stack
from cfme import test_requirements
from utils import testgen
from utils.path import orchestration_path
from utils.datafile import load_data_file
from utils.log import logger
from utils.wait import wait_for
from utils.blockers import BZ


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("upstream"),
    test_requirements.stack,
    pytest.mark.tier(2)
]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[
        ['provisioning', 'stack_provisioning']
    ],
    scope="module")


@pytest.yield_fixture(scope="function")
def template(provider, provisioning, dialog_name, setup_provider):
    template_type = provisioning['stack_provisioning']['template_type']
    template_name = fauxfactory.gen_alphanumeric()
    template = OrchestrationTemplate(template_type=template_type,
                                     template_name=template_name)

    if provider.type == "ec2":
        data_file = load_data_file(str(orchestration_path.join('aws_vm_template.json')))
    elif provider.type == "openstack":
        data_file = load_data_file(str(orchestration_path.join('openstack_vm_template.data')))
    elif provider.type == "azure":
        data_file = load_data_file(str(orchestration_path.join('azure_vm_template.json')))

    template.create(data_file.read().replace('CFMETemplateName', template_name))
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
def update_dialog(dialog_name):
    service_name = fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name="service_name",
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box=service_name
    )
    service_dialog = ServiceDialog(label=dialog_name, tab_label="Basic Information",
        box_label="Options", element_data=element_data)
    service_dialog.update_dialog_element(element_data)
    yield service_dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + fauxfactory.gen_alphanumeric()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(template, update_dialog, catalog, provider):
    item_name = update_dialog.element_data.get("default_text_box")

    catalog_item = CatalogItem(item_type="Orchestration",
                               name=item_name,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=update_dialog.label,
                               orch_template=template,
                               provider=provider)
    catalog_item.create()

    yield catalog_item, item_name


def random_desc():
    return fauxfactory.gen_alphanumeric()


def prepare_stack_data(provider, provisioning):
    stackname = "test" + fauxfactory.gen_alphanumeric()
    vm_name = "test" + fauxfactory.gen_alphanumeric()
    if provider.type == "azure":
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
            'user_image': user_image,
            'os_type': os_type,
            'vm_size': vm_size
        }
    elif provider.type == 'openstack':
        stack_prov = provisioning['stack_provisioning']

        stack_data = {
            'stack_name': stackname,
            'key': stack_prov['key_name'],
            'flavor': stack_prov['instance_type'],
        }
    else:
        stack_prov = provisioning['stack_provisioning']

        stack_data = {
            'stack_name': stackname,
            'vm_name': vm_name,
            'key_name': stack_prov['key_name'],
            'select_instance_type': stack_prov['instance_type'],
            'ssh_location': provisioning['ssh_location']
        }
    return stack_data


# BZ 1439942 for ec2,so skipping for ec2
@pytest.mark.uncollectif(lambda provider: provider.type == 'ec2')
def test_provision_stack(setup_provider, provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)

    service_catalogs = ServiceCatalogs(catalog_item.catalog, item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(item_name))
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2500, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text


# BZ 1439942 for ec2,so skipping for ec2
@pytest.mark.meta(blockers=[BZ(1439942, forced_streams=["5.6", "5.7", "upstream"])])
@pytest.mark.meta(blockers=[BZ(1442920, forced_streams=["5.7", "5.8", "upstream"])])
@pytest.mark.uncollectif(lambda provider: provider.type == 'ec2')
def test_reconfigure_service(provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)

    service_catalogs = ServiceCatalogs(catalog_item.catalog, item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(item_name))
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2000, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text

    myservice = MyService(catalog_item.name)
    myservice.reconfigure_service()


# BZ 1439942 for ec2,so skipping only for ec2
@pytest.mark.uncollectif(lambda provider: provider.type == 'ec2')
def test_remove_template_provisioning(provider, provisioning, catalog, catalog_item, template):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    stack_data = prepare_stack_data(provider, provisioning)
    service_catalogs = ServiceCatalogs(catalog_item.catalog, item_name, stack_data)
    service_catalogs.order()
    # This is part of test - remove template and see if provision fails , so not added as finalizer
    template.delete()
    row_description = 'Provisioning Service [{}] from [{}]'.format(item_name, item_name)
    cells = {'Description': row_description}
    wait_for(lambda: requests.find_request(cells), num_sec=500, delay=20)
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Service_Template_Provisioning failed'


# BZ 1439942 for ec2,so skipping for ec2
@pytest.mark.uncollectif(lambda provider: provider.type == 'ec2')
def test_retire_stack(provider, provisioning, catalog, catalog_item, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    catalog_item, item_name = catalog_item
    DefaultView.set_default_view("Stacks", "Grid View")

    stack_data = prepare_stack_data(provider, provisioning)
    service_catalogs = ServiceCatalogs(catalog_item.catalog, item_name, stack_data)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(item_name))
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=2500, delay=20)

    assert 'Provisioned Successfully' in row.last_message.text

    stack = Stack(stack_data['stack_name'], provider=provider)
    stack.wait_for_appear()
    stack.retire_stack()

    @request.addfinalizer
    def _cleanup_vms():
        clean_up(stack_data, provider)


def clean_up(stack_data, provider):
    try:
        # stack_exist returns 400 if stack ID not found, which triggers an exception
        if provider.mgmt.stack_exist(stack_data['stack_name']):
            wait_for(lambda: provider.mgmt.delete_stack(stack_data['stack_name']),
                     delay=10, num_sec=800, message="wait for stack delete")
        if provider.type == 'azure' and provider.mgmt.does_vm_exist(stack_data['vm_name']):
            wait_for(lambda: provider.mgmt.delete_vm(stack_data['vm_name']),
                     delay=10, num_sec=800, message="wait for vm delete")
        catalog_item.orch_template.delete()
    except Exception as ex:
        logger.warning('Exception while checking/deleting stack, continuing: {}'
                       .format(ex.message))
        pass
