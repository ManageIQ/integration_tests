# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.services.catalogs.myservice import MyService
from cfme.automate.simulation import simulate
from cfme.automate.explorer import Domain, Namespace, Class, Method
from cfme.web_ui import flash
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
from utils import version

pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles="+automate")
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.yield_fixture(scope="function")
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
                     tab_label="tab_" + fauxfactory.gen_alphanumeric(), tab_desc="my tab desc",
                     box_label="box_" + fauxfactory.gen_alphanumeric(), box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(provider, provisioning, vm_name, dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
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

    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=template,
                  provider=provider.name, prov_data=provisioning_data)
    yield catalog_item


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture
def myservice(setup_provider, provider, catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service {}'
        .format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'
    return MyService(catalog_item.name, vm_name)


def test_add_vm_to_service(myservice, request, copy_domain):
    """Tests adding vm to service

    Metadata:
        test_flag: provision
    """
    method_torso = """
    def add_to_service
        vm      = $evm.root['vm']
        service = $evm.vmdb('service').find_by_name('%s')
        user    = $evm.root['user']

    if service && vm
        $evm.log('info', "XXXXXXXX Attaching Service to VM: [#{service.name}][#{vm.name}]")
        vm.add_to_service(service)
        vm.owner = user if user
        vm.group = user.miq_group if user
    end
    end

    $evm.log("info", "Listing Root Object Attributes:")
    $evm.log("info", "===========================================")

    add_to_service
    """ % myservice.service_name

    method = Method(
        name="InspectMe",
        data=method_torso,
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=copy_domain
            )
        )
    )
    method.create()
    request.addfinalizer(lambda: method.delete() if method.exists() else None)
    simulate(
        instance="Request",
        message="create",
        request=method.name,
        attribute=["VM and Instance", "auto_test_services"],  # Random selection, does not matter
        execute_methods=True
    )
    myservice.check_vm_add("auto_test_services")
    request.addfinalizer(lambda: myservice.delete(myservice.service_name))
