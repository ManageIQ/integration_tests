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
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for
from utils import version
import utils.randomness as rand

pytestmark = [
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("5.2")
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name + "_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


@pytest.fixture
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    element_data = dict(
        ele_label="ele_" + rand.generate_random_string(),
        ele_name=rand.generate_random_string(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True,
                                   tab_label="tab_" + rand.generate_random_string(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + rand.generate_random_string(),
                                   box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    return service_dialog


@pytest.fixture(scope="function")
def catalog():
    catalog = "cat_" + generate_random_string()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    return cat


@pytest.fixture(scope="function")
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
        catalog_item_type = version.pick({
            version.LATEST: "RHEV",
            '5.3': "RHEV",
            '5.2': "Redhat"
        })
    elif provider_type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
    item_name = generate_random_string()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                               description="my catalog", display_in=True,
                               catalog=catalog.name, dialog=dialog.label,
                               catalog_name=template,
                               provider=provider_crud.name,
                               prov_data=provisioning_data)
    return catalog_item


@pytest.fixture
def myservice(provider_init, provider_key, provider_mgmt, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service {}'
        .format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert row.last_message.text == 'Request complete'
    return MyService(catalog_item.name, vm_name)


@pytest.mark.meta(blockers=[1204899])
def test_retire_service(myservice):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    myservice.retire()


@pytest.mark.meta(blockers=[1204899])
def test_retire_service_on_date(myservice):
    """Tests my service retirement

    Metadata:
        test_flag: provision
    """
    dt = datetime.utcnow()
    myservice.retire_on_date(dt)


@pytest.mark.meta(blockers=[1204899])
def test_myservice_crud(myservice):
    """Tests my service crud

    Metadata:
        test_flag: provision
    """
    myservice.update("edited", "edited_desc")
    edited_name = myservice.service_name + "_" + "edited"
    myservice.delete(edited_name)


@pytest.mark.meta(blockers=[1204899])
def test_set_ownership(myservice):
    """Tests my service ownership

    Metadata:
        test_flag: provision
    """
    myservice.set_ownership("Administrator", "EvmGroup-administrator")


@pytest.mark.meta(blockers=[1204899])
def test_edit_tags(myservice):
    """Tests my service edit tags

    Metadata:
        test_flag: provision
    """
    myservice.edit_tags("Cost Center 001")
