import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.myservice import MyService
from cfme.services import requests
from cfme.web_ui import flash
from datetime import datetime
from utils import testgen
from utils.randomness import generate_random_string
from utils.providers import setup_infrastructure_providers
from utils.log import logger
from utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.fixtureconf(server_roles="+automate")
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_infrastructure_providers()


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True)
    service_dialog.create()
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + generate_random_string()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(provider_crud, provider_type,
                 provisioning, vm_name, dialog, catalog):
    template, host, datastore, iso_file, catalog_item_type = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type'))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    if provider_type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
        provisioning_data['vlan'] = provisioning['vlan']
    elif provider_type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
    item_name = generate_random_string()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                               description="my catalog", display_in=True,
                               catalog=catalog, dialog=dialog,
                               catalog_name=template,
                               provider=provider_crud.name,
                               prov_data=provisioning_data)
    yield catalog_item


def test_retire_service(catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s'
                % catalog_item.name)
    row_description = 'Provisioning [%s] for Service [%s]' \
        % (catalog_item.name, catalog_item.name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=600, delay=20)
    assert row.last_message.text == 'Request complete'
    myservice = MyService(catalog_item.name, vm_name)
    myservice.retire()


def test_retire_service_on_date(catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s'
                % catalog_item.name)
    row_description = 'Provisioning [%s] for Service [%s]' \
        % (catalog_item.name, catalog_item.name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=600, delay=20)
    assert row.last_message.text == 'Request complete'
    dt = datetime.utcnow()
    myservice = MyService(catalog_item.name, vm_name)
    myservice.retire_on_date(dt)
