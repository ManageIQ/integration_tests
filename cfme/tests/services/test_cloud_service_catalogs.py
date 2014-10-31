import pytest

from cfme.services.catalogs import cloud_catalog_item as cct
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.web_ui import flash
from utils import testgen
from utils.randomness import generate_random_string
from utils.providers import setup_provider
from utils.log import logger
from utils.wait import wait_for
import utils.randomness as rand


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.ignore_stream("5.2")
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
        if not {'image'}.issubset(args['provisioning'].viewkeys()):
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


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True,
                                   tab_label="tab_" + rand.generate_random_string(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + rand.generate_random_string(),
                                   box_desc="my box desc",
                                   ele_label="ele_" + rand.generate_random_string(),
                                   ele_name=rand.generate_random_string(),
                                   ele_desc="my ele desc", choose_type="Text Box",
                                   default_text_box="default value")
    service_dialog.create()
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + generate_random_string()
    catalog = Catalog(name=cat_name, description="my catalog")
    catalog.create()
    yield catalog


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name + "_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


@pytest.mark.bugzilla(1131330)
def test_cloud_catalog_item(provider_init, provider_key, provider_mgmt, provider_crud,
                            provider_type, provisioning, dialog, catalog, request):
    vm_name = 'test_servicecatalog-%s' % generate_random_string()
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
    image = provisioning['image']['name']
    item_name = generate_random_string()

    cloud_catalog_item = cct.Instance(
        item_type=provisioning['item_type'],
        name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog.name,
        dialog=dialog,
        catalog_name=image,
        vm_name=vm_name,
        instance_type=provisioning['instance_type'],
        availability_zone=provisioning['availability_zone'],
        cloud_tenant=provisioning['cloud_tenant'],
        cloud_network=provisioning['cloud_network'],
        security_groups=[provisioning['security_group']],
        provider_mgmt=provider_mgmt,
        provider=provider_crud.name,
        guest_keypair=provisioning['guest_keypair'])

    cloud_catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog.name, cloud_catalog_item)
    flash.assert_no_errors()
    logger.info('Waiting for cfme provision request for service %s' % item_name)
    row_description = 'Provisioning [%s] for Service [%s]' %\
        (item_name, item_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=1000, delay=20)
    assert row.last_message.text == 'Request complete'
