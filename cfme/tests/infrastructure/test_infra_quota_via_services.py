# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
# from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.configure.access_control import Tenant
from cfme.services import requests
from cfme.web_ui import flash
from utils import testgen
from utils.log import logger
from utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'uses_infra_providers'),
    test_requirements.quota
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(metafunc, [VMwareProvider],
        required_fields=[
            ['provisioning', 'template'],
            ['provisioning', 'host'],
            ['provisioning', 'datastore']
    ])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


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
                                   tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + fauxfactory.gen_alphanumeric(),
                                   box_desc="my box desc")
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


@pytest.yield_fixture(scope="module")
def set_tenant_cpu():
    cpu_data = {'cpu_cb': True, 'cpu': 2}
    reset_cpu_data = {'cpu_cb': False}
    roottenant = Tenant.get_root_tenant()
    roottenant.set_quota(**cpu_data)
    yield
    roottenant.set_quota(**reset_cpu_data)


@pytest.yield_fixture(scope="module")
def set_tenant_memory():
    memory_data = {'memory_cb': True, 'memory': 2}
    reset_memory_data = {'memory_cb': False}
    roottenant = Tenant.get_root_tenant()
    roottenant.set_quota(**memory_data)
    yield
    roottenant.set_quota(**reset_memory_data)


@pytest.yield_fixture(scope="module")
def set_tenant_storage():
    storage_data = {'storage_cb': True, 'storage': 1}
    reset_storage_data = {'storage_cb': False}
    roottenant = Tenant.get_root_tenant()
    roottenant.set_quota(**storage_data)
    yield
    roottenant.set_quota(**reset_storage_data)


@pytest.yield_fixture(scope="module")
def set_tenant_vm():
    vm_data = {'vm_cb': True, 'vm': 1}
    reset_vm_data = {'vm_cb': False}
    roottenant = Tenant.get_root_tenant()
    roottenant.set_quota(**vm_data)
    yield
    roottenant.set_quota(**reset_vm_data)


@pytest.fixture(scope="function")
def provisioning_data(provider, vm_name, provisioning):
    template, host, datastore, iso_file, catalog_item_type, vlan = map(provisioning.get,
        ('template', 'host', 'datastore', 'iso_file', 'catalog_item_type', 'vlan'))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'vlan': vlan,
        'template': template,
        'provision_type': "Native Clone" if provider.type == "rhevm" else "VMware",
        'catalog_item_type': catalog_item_type,
        'item_name': fauxfactory.gen_alphanumeric()
    }
    return provisioning_data


@pytest.mark.tier(1)
def test_tenant_infra_cpu_quota_via_services(provisioning_data, provider, setup_provider, request,
        vm_name, set_tenant_cpu, dialog, catalog):
    """Test Tenant Quota-Max CPU by services using default entry point.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for cpu by UI enforcement
        * Create dialog and catalog.
        * Create a catalog item by setting CPU greater then tenant quota cpu.
        * Order the service and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    provisioning_data = dict(
        provisioning_data,
        num_sockets="8"
    )
    catalog_item = CatalogItem(item_type=provisioning_data['catalog_item_type'],
                    name=provisioning_data['item_name'], description="my catalog",
                    display_in=True, catalog=catalog, dialog=dialog,
                    catalog_name=provisioning_data['template'], provider=provider,
                    prov_data=provisioning_data)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(service_name=catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.reason.text == "Quota Exceeded"


@pytest.mark.tier(1)
def test_tenant_infra_memory_quota_via_services(provisioning_data, provider, setup_provider,
        request, vm_name, set_tenant_memory, dialog, catalog):
    """Test Tenant Quota-Max Memory by services using default entry point.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for memory by UI enforcement
        * Create dialog and catalog.
        * Create a catalog item by setting memory greater then tenant quota memory.
        * Order the service and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    provisioning_data = dict(
        provisioning_data,
        memory="4096"
    )
    catalog_item = CatalogItem(item_type=provisioning_data['catalog_item_type'],
                    name=provisioning_data['item_name'], description="my catalog",
                    display_in=True, catalog=catalog, dialog=dialog,
                    catalog_name=provisioning_data['template'], provider=provider,
                    prov_data=provisioning_data)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(service_name=catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.reason.text == "Quota Exceeded"


@pytest.mark.tier(1)
def test_tenant_infra_storage_quota_via_services(provisioning_data, provider, setup_provider,
        request, vm_name, set_tenant_storage, dialog, catalog):
    """Test Tenant Quota-Max Storage by services using default entry point.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for Stoarge by UI enforcement
        * Create dialog and catalog.
        * Create a catalog item by selecting template with storage greater then tenant quota storage
        * Order the service and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    provisioning_data = dict(
        provisioning_data
    )
    catalog_item = CatalogItem(item_type=provisioning_data['catalog_item_type'],
                    name=provisioning_data['item_name'], description="my catalog",
                    display_in=True, catalog=catalog, dialog=dialog,
                    catalog_name=provisioning_data['template'], provider=provider,
                    prov_data=provisioning_data)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(service_name=catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.reason.text == "Quota Exceeded"


@pytest.mark.tier(1)
def test_tenant_infra_vm_quota_via_services(provisioning_data, provider, setup_provider, request,
        vm_name, set_tenant_vm, dialog, catalog):
    """Test Tenant Quota-Max Vms by services using default entry point.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for vms by UI enforcement
        * Create dialog and catalog.
        * Create a catalog item by setting number of vms greater then tenant quota vms.
        * Order the service and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    provisioning_data = dict(
        provisioning_data,
        num_vms="4"
    )
    catalog_item = CatalogItem(item_type=provisioning_data['catalog_item_type'],
                    name=provisioning_data['item_name'], description="my catalog",
                    display_in=True, catalog=catalog, dialog=dialog,
                    catalog_name=provisioning_data['template'], provider=provider,
                    prov_data=provisioning_data)
    catalog_item.create()
    service_catalogs = ServiceCatalogs(service_name=catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.reason.text == "Quota Exceeded"
