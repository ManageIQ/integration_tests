import pytest
import cfme.web_ui.flash as flash
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs import Catalog
from utils.providers import setup_infrastructure_providers
from utils.randomness import generate_random_string
from utils import testgen, error
from utils.update import update
from utils.log import logger

pytestmark = [pytest.mark.usefixtures("logged_in")]

pytestmark = [pytest.mark.usefixtures("logged_in")]


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
def vm_name(provider_key, provider_mgmt):
    # also tries to delete the VM that gets made with this name
    vm_name = 'provtest-%s' % generate_random_string()
    yield vm_name
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog,
                  description="my dialog", submit=True, cancel=True)
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
def catalog_item(provider_crud, provider_type, provisioning, vm_name, dialog, catalog):
    template, host, datastore, iso_file, catalog_item_type = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type'))
    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    if provider_type == 'rhevm':
        provisioning_data['vlan'] = provisioning['vlan']
        provisioning_data['iso_file'] = {'name': [iso_file]}

    catalog_item = CatalogItem(item_type=catalog_item_type, name=generate_random_string(),
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=template,
                  provider=provider_crud.name, prov_data=provisioning_data)
    yield catalog_item


def test_create_catalog_item(setup_providers, catalog_item):
    catalog_item.create()


def test_update_catalog_item(setup_providers, catalog_item):
    catalog_item.create()
    with update(catalog_item):
        catalog_item.description = "my edited description"


def test_delete_catalog_item(setup_providers, catalog_item):
    catalog_item.create()
    catalog_item.delete()


def test_catalog_item_duplicate_name(setup_providers, catalog_item):
    catalog_item.create()
    with error.expected("Name has already been taken"):
        catalog_item.create()
