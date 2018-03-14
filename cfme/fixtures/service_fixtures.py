# -*- coding: utf-8 -*-
import pytest
from widgetastic.utils import partial_match

from cfme.common.provider import cleanup_vm
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
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
    catalog_item_type = provider.catalog_name
    provision_type, template, host, datastore, iso_file, vlan = map(provisioning.get,
        ('provision_type', 'template', 'host', 'datastore', 'iso_file', 'vlan'))
    if console_template:
        logger.info("Console template name : {}".format(console_template.name))
        template = console_template.name
    item_name = dialog.label
    if provider.one_of(InfraProvider):
        catalog_name = template
        provisioning_data = {
            'catalog': {'vm_name': vm_name,
                        'provision_type': provision_type},
            'environment': {'host_name': {'name': host},
                            'datastore_name': {'name': datastore}},
            'network': {'vlan': partial_match(vlan)},
        }
    elif provider.one_of(CloudProvider):
        catalog_name = provisioning['image']['name']
        provisioning_data = {
            'catalog': {'vm_name': vm_name},
            'properties': {'instance_type': partial_match(provisioning['instance_type']),
                           'guest_keypair': provisioning['guest_keypair'],
                           'boot_disk_size': provisioning.get('boot_disk_size', None)},
            'environment': {'availability_zone': provisioning['availability_zone'],
                            'cloud_network': provisioning['cloud_network']}
        }
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog, catalog_name=catalog_name,
        provider=provider, prov_data=provisioning_data)
    catalog_item.create()
    return catalog_item


@pytest.fixture
def order_service(appliance, provider, provisioning, vm_name,
                  dialog, catalog, console_template, request):
    """ Orders service once the catalog item is created"""
    if hasattr(request, 'param'):
        catalog_item = create_catalog_item(provider, provisioning, vm_name, dialog, catalog,
                                           console_template if 'console_test' in request.param else None)
    else:
        catalog_item = create_catalog_item(provider, provisioning, vm_name, dialog, catalog)
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog,
                                       catalog_item.name)
    service_catalogs.order()
    return catalog_item


@pytest.fixture
def provision_request(appliance, order_service):
    """Checks if the service request is completed and provisioned"""
    catalog_item = order_service
    provision_request = appliance.collections.requests.instantiate(catalog_item.name,
                                                                   partial_check=True)
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded()
    return catalog_item, provision_request
# TODO - remove request finally
