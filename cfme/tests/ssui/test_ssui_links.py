# -*- coding: utf-8 -*-
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from utils.log import logger
from utils.wait import wait_for
from utils import testgen
from cfme.ssui import ssui_links
from fixtures.pytest_store import store
from utils import browser
from cfme.fixtures import pytest_selenium as sel

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'vm_name', 'catalog_item', 'uses_infra_providers'),
    pytest.mark.long_running
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc,
        required_fields=[
            ['provisioning', 'template'],
            ['provisioning', 'host'],
            ['provisioning', 'datastore']
        ])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def revert_to_default():
    store.current_appliance.mode = "default"
    browser.quit()


@pytest.fixture(scope="module", autouse=True)
def set_ssui_mode(request):
    store.current_appliance.mode = "ssui"


@pytest.fixture
def order_catalog_item(provider, setup_provider, catalog_item, request):
    """order catalog item
    """
    store.current_appliance.mode = "default"
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
       fail_func=requests.reload, num_sec=1200, delay=20)
    assert row.last_message.text == 'Request complete'
    return catalog_item.name


def test_ssui_links(order_catalog_item, request):
    catalog_item_name = order_catalog_item
    browser.quit()
    store.current_appliance.mode = "ssui"
    sel.ssui_force_navigate('My Services')
    ssui_links.go_to('My Services')
    ssui_links.find_row("{}".format(catalog_item_name))

    ssui_links.edit_service(catalog_item_name)
    ssui_links.go_to('My Requests')
    ssui_links.find_row("Provisioning Service [{}] from [{}]"
        .format(catalog_item_name, catalog_item_name))
    ssui_links.go_to('Service Catalog')
    ssui_links.find_service_card("{}".format(catalog_item_name))
    request.addfinalizer(revert_to_default)
