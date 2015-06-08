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
from utils.providers import setup_provider
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.ignore_stream("5.2", "5.3", "upstream")
]


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


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


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


def test_provision_stack(provider_init, provider_key, provider_crud,
                        provider_type, provisioning, dialog, catalog, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    dialog_name, template_name = dialog
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog_name, orch_template=template_name,
                  provider_type=provider_crud.name)
    catalog_item.create()
    if provider_type == 'ec2':
        stack_data = {
            'stack_name': "stack" + fauxfactory.gen_alphanumeric(),
            'key_name': provisioning['stack_provisioning']['key_name'],
            'db_user': provisioning['stack_provisioning']['db_user'],
            'db_password': provisioning['stack_provisioning']['db_password'],
            'db_root_password': provisioning['stack_provisioning']['db_root_password'],
            'select_instance_type': provisioning['stack_provisioning']['instance_type'],
        }
    elif provider_type == 'openstack':
        stack_data = {
            'stack_name': "stack" + fauxfactory.gen_alphanumeric()
        }
    service_catalogs = ServiceCatalogs("service_name", stack_data)
    service_catalogs.order_stack_item(catalog.name, catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % item_name)
    row_description = item_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Service Provisioned Successfully'


@pytest.mark.meta(blockers=[1221333])
def test_reconfigure_service(provider_init, provider_key, provider_crud,
                        provider_type, provisioning, dialog, catalog, request):
    """Tests stack provisioning

    Metadata:
        test_flag: provision
    """
    dialog_name, template_name = dialog
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="Orchestration", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog_name, orch_template=template_name,
                  provider_type=provider_crud.name)
    catalog_item.create()
    if provider_type == 'ec2':
        stack_data = {
            'stack_name': fauxfactory.gen_alphanumeric(),
            'key_name': provisioning['stack_provisioning']['key_name'],
            'db_user': provisioning['stack_provisioning']['db_user'],
            'db_password': provisioning['stack_provisioning']['db_password'],
            'db_root_password': provisioning['stack_provisioning']['db_root_password'],
            'select_instance_type': provisioning['stack_provisioning']['instance_type'],
        }
    elif provider_type == 'openstack':
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
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Service Provisioned Successfully'
    myservice = MyService(catalog_item.name)
    myservice.reconfigure_service()
