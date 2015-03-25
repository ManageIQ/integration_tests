import pytest

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
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for
from utils import version
import utils.randomness as rand

pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("5.2"),
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles="+automate")
]

item_name = generate_random_string()

METHOD_TORSO = """
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
""" % item_name


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.yield_fixture(scope="function")
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
                     tab_label="tab_" + rand.generate_random_string(), tab_desc="my tab desc",
                     box_label="box_" + rand.generate_random_string(), box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + generate_random_string()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name + "_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


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
        provisioning_data['provision_type'] = 'Native Clone'
        provisioning_data['vlan'] = provisioning['vlan']
        catalog_item_type = version.pick({
            version.LATEST: "RHEV",
            '5.3': "RHEV",
            '5.2': "Redhat"
        })
    elif provider_type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=template,
                  provider=provider_crud.name, prov_data=provisioning_data)
    yield catalog_item


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name=generate_random_string(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="function")
def create_method(request, copy_domain):
    method = Method(
        name="InspectMe",
        data=METHOD_TORSO,
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
    return method


@pytest.fixture
def myservice(provider_init, provider_key, provider_mgmt, catalog_item, request):
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
        fail_func=requests.reload, num_sec=900, delay=20)
    assert row.last_message.text == 'Request complete'
    return MyService(catalog_item.name, vm_name)


@pytest.mark.meta(blockers=[1204899])
def test_add_vm_to_service(request, myservice, create_method):
    """Tests adding vm to service

    Metadata:
        test_flag: provision
    """

    simulate(
        instance="Request",
        message="create",
        request=create_method.name,
        attribute=["VM and Instance", "auto_test_services"],  # Random selection, does not matter
        execute_methods=True
    )
    myservice.check_vm_add("auto_test_services")
    request.addfinalizer(lambda: myservice.delete(item_name))
