import pytest

import cfme.web_ui.flash as flash
from cfme.services.catalogs.catalog_item import CatalogItem
from utils import testgen
import utils.randomness as rand
from utils.randomness import generate_random_string
from utils.log import logger


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


def test_create_catalog_item(provider_crud, provider_type, provisioning, vm_name):
	template, host, datastore , catalog_item_type= map(provisioning.get,
        ('template', 'host', 'datastore', 'catalog_item_type'))
	provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
        }

        if provider_type == 'rhevm':
            provisioning_data['vlan'] = provisioning['vlan']

	cat_item = CatalogItem(item_type=catalog_item_type, name=rand.generate_random_string(),
                  description="my catalog", display_in=True, catalog="auto_cat_1MnAggj0", dialog="auto_dialog_1MnAggj0",
                  long_desc=None, catalog_name=template, provider=provider_crud.name, prov_data = provisioning_data)
    	cat_item.create()
    	flash.assert_no_errors()
