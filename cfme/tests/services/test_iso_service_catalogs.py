# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.infrastructure.pxe import get_template_from_config, ISODatastore
from cfme.services import requests
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
from utils.conf import cfme_data

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'vm_name', 'uses_infra_providers'),
    pytest.mark.ignore_stream("5.2")
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')
    argnames = argnames + ['iso_cust_template', 'iso_datastore']

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        provider_data = cfme_data.get('management_systems', {})[
            argvalue_tuple[argnames.index('provider_key')]]
        if not provider_data.get('iso_datastore', False):
            continue

        # required keys should be a subset of the dict keys set
        if not {'iso_template', 'host', 'datastore',
                'iso_file', 'iso_kickstart',
                'iso_root_password',
                'iso_image_type', 'vlan'}.issubset(args['provisioning'].viewkeys()):
            # Need all  for template provisioning
            continue

        iso_cust_template = args['provisioning']['iso_kickstart']
        if iso_cust_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_template_from_config(iso_cust_template))
        argvalues[i].append(ISODatastore(provider_data['name']))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name + "_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


@pytest.fixture(scope="module")
def setup_iso_datastore(setup_provider, iso_cust_template, provisioning, iso_datastore):
    if not iso_datastore.exists():
        iso_datastore.create()
    iso_datastore.set_iso_image_type(provisioning['iso_file'], provisioning['iso_image_type'])
    if not iso_cust_template.exists():
        iso_cust_template.create()


@pytest.yield_fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name="service_name",
        ele_desc="ele_desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + fauxfactory.gen_alphanumeric(), tab_desc="tab_desc",
                     box_label="box_" + fauxfactory.gen_alphanumeric(), box_desc="box_desc")
    service_dialog.create(element_data)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.yield_fixture(scope="function")
def catalog_item(setup_provider, provider_crud, provider_type, provisioning, vm_name, dialog,
                 catalog):
    iso_template, host, datastore, iso_file, iso_kickstart,\
        iso_root_password, iso_image_type, vlan = map(provisioning.get, ('pxe_template', 'host',
                                'datastore', 'iso_file', 'iso_kickstart',
                                'iso_root_password', 'iso_image_type', 'vlan'))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'ISO',
        'iso_file': {'name': [iso_file]},
        'custom_template': {'name': [iso_kickstart]},
        'root_password': iso_root_password,
        'vlan': vlan
    }

    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type="RHEV", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, catalog_name=iso_template,
                  provider=provider_crud.name, prov_data=provisioning_data)
    yield catalog_item


@pytest.mark.meta(blockers=[1206654, 1207209])
@pytest.mark.usefixtures('setup_iso_datastore')
def test_rhev_iso_servicecatalog(setup_provider, provider_key, provider_mgmt,
                                 catalog_item, request):
    """Tests RHEV ISO service catalog

    Metadata:
        test_flag: iso, provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for service %s' % catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1800, delay=20)
    assert row.last_message.text == 'Request complete'
