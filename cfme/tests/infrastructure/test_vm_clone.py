# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.web_ui import flash
from utils.wait import wait_for
from utils import testgen
from utils.log import logger
from utils import version

pytestmark = [
    pytest.mark.meta(roles="+automate")
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc", choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + fauxfactory.gen_alphanumeric(), tab_desc="my tab desc",
                     box_label="box_" + fauxfactory.gen_alphanumeric(), box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "{}" was added'.format(dialog))
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(provider, vm_name, dialog, catalog, provisioning):
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
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=template,
                  provider=provider, prov_data=provisioning_data)
    yield catalog_item


@pytest.fixture(scope="function")
def clone_vm_name():
    clone_vm_name = 'test_cloning_{}'.format(fauxfactory.gen_alphanumeric())
    return clone_vm_name


@pytest.fixture
def create_vm(provider, setup_provider, catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.name)
    service_catalogs.order()
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert row.last_message.text == 'Request complete'
    return vm_name


@pytest.mark.meta(blockers=[1255190])
@pytest.mark.usefixtures("setup_provider")
@pytest.mark.uncollectif(version.appliance_is_downstream())
@pytest.mark.long_running
def test_vm_clone(provider, clone_vm_name, request, create_vm):
    vm_name = create_vm + "_0001"
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    request.addfinalizer(lambda: cleanup_vm(clone_vm_name, provider))
    vm = VM.factory(vm_name, provider)
    if provider.type == 'rhevm':
        provision_type = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provision_type = 'VMware'
    vm.clone_vm("email@xyz.com", "first", "last", clone_vm_name, provision_type)
    row_description = clone_vm_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=4000, delay=20)
    assert row.last_message.text == 'Vm Provisioned Successfully'
