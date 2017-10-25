# -*- coding: utf-8 -*-
import pytest

from cfme.common.provider import cleanup_vm
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import service_catalog_obj as _catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.log import logger


@pytest.fixture(scope="function")
def dialog(request, appliance):
    return _dialog(request, appliance)


@pytest.yield_fixture(scope="function")
def catalog(request, appliance):
    return _catalog(request, appliance.rest_api)


@pytest.fixture(scope="function")
def catalog_item(provider, provisioning, vm_name, dialog, catalog):
    catalog_item = create_catalog_item(provider, provisioning, vm_name, dialog, catalog)
    return catalog_item


def create_catalog_item(provider, provisioning, vm_name, dialog, catalog, console_template=None):

    template, host, datastore, iso_file, catalog_item_type, vlan = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type', 'vlan'))
    if console_template:
        logger.info("Console template name : {}".format(console_template.name))
        template = console_template.name
    item_name = dialog.label

    provisioning_data = {
        'catalog': {'vm_name': vm_name,
                    },
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore},
                        },
        'network': {'vlan': vlan,
                    },
    }

    if provider.type == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog, catalog_name=template,
        provider=provider, prov_data=provisioning_data)
    return catalog_item


@pytest.fixture(scope="function")
def order_catalog_item_in_ops_ui(appliance, provider, provisioning, vm_name, dialog, catalog,
        console_template, request):
    """
        Fixture for SSUI tests.
        Orders catalog item in OPS UI.
    """
    if hasattr(request, 'param'):
        catalog_item = create_catalog_item(provider, provisioning, vm_name, dialog, catalog,
            console_template if 'console_test' in request.param else None)
    else:
        catalog_item = create_catalog_item(provider, provisioning, vm_name, dialog, catalog)
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    request.addfinalizer(lambda: cleanup_vm("{}0001".format(vm_name), provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info("Waiting for cfme provision request for service {}".format(catalog_item.name))
    request_description = catalog_item.name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    assert provision_request.is_finished()
    return catalog_item
