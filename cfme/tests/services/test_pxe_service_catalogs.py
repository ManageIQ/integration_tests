import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.infrastructure.pxe import get_pxe_server_from_config, get_template_from_config
from cfme.services import requests
from utils import testgen
from utils.randomness import generate_random_string
from utils.providers import setup_infrastructure_providers
from utils.log import logger
from utils.wait import wait_for
from utils.conf import cfme_data

pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.usefixtures("vm_name"),
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.usefixtures('server_roles', 'uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')
    pargnames, pargvalues, pidlist = testgen.pxe_servers(metafunc)
    argnames = argnames + ['pxe_server', 'pxe_cust_template']
    pxe_server_names = [pval[0] for pval in pargvalues]

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'pxe_template', 'host', 'datastore',
                'pxe_server', 'pxe_image', 'pxe_kickstart',
                'pxe_root_password',
                'pxe_image_type', 'vlan'}.issubset(args['provisioning'].viewkeys()):
            # Need all  for template provisioning
            continue

        pxe_server_name = args['provisioning']['pxe_server']
        if pxe_server_name not in pxe_server_names:
            continue

        pxe_cust_template = args['provisioning']['pxe_kickstart']
        if pxe_cust_template not in cfme_data['customization_templates'].keys():
            continue

        argvalues[i].append(get_pxe_server_from_config(pxe_server_name))
        argvalues[i].append(get_template_from_config(pxe_cust_template))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_pxe_servers_vm_prov(pxe_server, pxe_cust_template, provisioning):
    if not pxe_server.exists():
        pxe_server.create()
    pxe_server.set_pxe_image_type(provisioning['pxe_image'], provisioning['pxe_image_type'])
    if not pxe_cust_template.exists():
        pxe_cust_template.create()


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_infrastructure_providers()

def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name+"_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))



@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + generate_random_string(), tab_desc="tab_desc",
                     box_label="box_" + generate_random_string(), box_desc="box_desc",
                     ele_label="ele_" + generate_random_string(),
                     ele_name="service_name",
                     ele_desc="ele_desc", choose_type="Text Box", default_text_box="default value")
    service_dialog.create()
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
    # generate_tests makes sure these have values
    pxe_template, host, datastore, pxe_server, pxe_image, pxe_kickstart,\
        pxe_root_password, pxe_image_type, pxe_vlan, catalog_item_type = map(provisioning.get, ('pxe_template', 'host',
                                'datastore', 'pxe_server', 'pxe_image', 'pxe_kickstart',
                                'pxe_root_password', 'pxe_image_type', 'vlan', 'catalog_item_type'))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'PXE',
        'pxe_server': pxe_server,
        'pxe_image': {'name': [pxe_image]},
        'custom_template': {'name': [pxe_kickstart]},
        'root_password': pxe_root_password,
        'vlan': pxe_vlan,
    }

    item_name = generate_random_string()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=pxe_template,
                  provider=provider_crud.name, prov_data=provisioning_data)
    yield catalog_item

@pytest.mark.usefixtures('setup_providers', 'setup_pxe_servers_vm_prov')
def test_rhev_pxe_servicecatalog(provider_key, provider_mgmt, catalog_item, request):
    vm_name = catalog_item.provisioning_data["vm_name"]
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for service %s' % catalog_item.name)
    row_description = 'Provisioning [%s] for Service [%s]' % (catalog_item.name, catalog_item.name)
    cells = {'Description': row_description}
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.last_message.text == 'Request complete'
