# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.myservice import MyService
from cfme.services import requests
from cfme.web_ui import flash
from datetime import datetime
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
from utils import version, browser
from utils.version import current_version
from utils.browser import ensure_browser_open

pytestmark = [
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("5.2")
]


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    ensure_browser_open()
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True,
                                   tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + fauxfactory.gen_alphanumeric(),
                                   box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    return service_dialog


@pytest.fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    return cat


@pytest.fixture(scope="function")
def catalog_item(provider, provisioning, vm_name, dialog, catalog):
    template, host, datastore, iso_file, catalog_item_type = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type'))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    if provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
        provisioning_data['vlan'] = provisioning['vlan']
        catalog_item_type = "RHEV"
    elif provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                               description="my catalog", display_in=True,
                               catalog=catalog.name, dialog=dialog.label,
                               catalog_name=template,
                               provider=provider.name,
                               prov_data=provisioning_data)
    return catalog_item


@pytest.fixture
def myservice(setup_provider, provider, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"] + "_0001"
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service {}'
        .format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=2000, delay=20)
    assert row.last_message.text == 'Request complete'
    return MyService(catalog_item.name, vm_name)


def test_retire_service(provider, myservice, register_event):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    myservice.retire()
    register_event(
        provider.get_yaml_data()['type'],
        "service", myservice.service_name, ["service_retired"])


def test_retire_service_on_date(myservice):
    """Tests my service retirement

    Metadata:
        test_flag: provision
    """
    dt = datetime.utcnow()
    myservice.retire_on_date(dt)


def test_crud_set_ownership_and_edit_tags(myservice):
    """Tests my service crud , edit tags and ownership

    Metadata:
        test_flag: provision
    """
    myservice.set_ownership("Administrator", "EvmGroup-administrator")
    myservice.edit_tags("Cost Center *", "Cost Center 001")
    myservice.update("edited", "edited_desc")
    edited_name = myservice.service_name + "_" + "edited"
    myservice.delete(edited_name)


@pytest.mark.uncollectif(lambda: current_version() < "5.5")
@pytest.mark.parametrize("filetype", ["Text", "CSV", "PDF"])
def test_download_file(needs_firefox, myservice, filetype):
    """Tests my service download files

    Metadata:
        test_flag: provision
    """
    myservice.download_file(filetype)
