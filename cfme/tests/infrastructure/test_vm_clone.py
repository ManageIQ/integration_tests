# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils import version

pytestmark = [
    pytest.mark.meta(roles="+automate")
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.yield_fixture(scope="function")
def catalog_item(provider, vm_name, dialog, catalog, provisioning):
    template, host, datastore, iso_file, catalog_item_type = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type'))

    provisioning_data = {
        'catalog': {'vm_name': vm_name,
                    },
        'environment': {'host_name': {'name': host},
                        'datastore_name': {'name': datastore},
                        },
        'network': {},
    }

    if provider.type == 'rhevm':
        provisioning_data['catalog']['provision_type'] = 'Native Clone'
        provisioning_data['network']['vlan'] = provisioning['vlan']
        catalog_item_type = "RHEV"
    elif provider.type == 'virtualcenter':
        provisioning_data['catalog']['provision_type'] = 'VMware'
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
def create_vm(appliance, provider, setup_provider, catalog_item, request):
    vm_name = catalog_item.provisioning_data['catalog']["vm_name"]
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    request_row = appliance.collections.requests.instantiate(request_description,
                                                             partial_check=True)
    request_row.wait_for_request()
    assert request_row.is_succeeded()
    return vm_name


@pytest.mark.usefixtures("setup_provider")
@pytest.mark.uncollectif(lambda: version.appliance_is_downstream())
@pytest.mark.long_running
def test_vm_clone(appliance, provider, clone_vm_name, request, create_vm):
    vm_name = create_vm + "_0001"
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    request.addfinalizer(lambda: cleanup_vm(clone_vm_name, provider))
    vm = VM.factory(vm_name, provider)
    if provider.one_of(RHEVMProvider):
        provision_type = 'Native Clone'
    elif provider.one_of(VMwareProvider):
        provision_type = 'VMware'
    vm.clone_vm("email@xyz.com", "first", "last", clone_vm_name, provision_type)
    request_description = clone_vm_name
    request_row = appliance.collections.requests.instantiate(request_description,
                                                             partial_check=True)
    request_row.wait_for_request(method='ui')
    assert request_row.is_succeeded(method='ui')
