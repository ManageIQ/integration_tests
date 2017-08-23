# -*- coding: utf-8 -*-
import pytest
from datetime import datetime

from cfme import test_requirements
from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services import requests
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.web_ui import toolbar as tb
from cfme.utils import browser, testgen, version
from cfme.utils.browser import ensure_browser_open
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.utils.update import update
from cfme.utils.version import appliance_is_downstream


pytestmark = [
    pytest.mark.usefixtures("vm_name", "catalog_item"),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(2)
]


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    ensure_browser_open()
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


pytest_generate_tests = testgen.generate([VMwareProvider], scope="module")


@pytest.yield_fixture(scope='function')
def myservice(setup_provider, provider, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = version.pick({
        version.LOWEST: catalog_item.provisioning_data["vm_name"] + '_0001',
        '5.7': catalog_item.provisioning_data["vm_name"] + '0001'})
    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                       fail_func=tb.refresh, num_sec=2000, delay=60)
    assert row.request_state.text == 'Finished'

    yield MyService(catalog_item.name, vm_name)

    cleanup_vm(vm_name, provider)


def test_retire_service(provider, myservice):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    myservice.retire()


def test_retire_service_on_date(myservice):
    """Tests my service retirement

    Metadata:
        test_flag: provision
    """
    dt = datetime.utcnow()
    myservice.retire_on_date(dt)


def test_crud_set_ownership_and_edit_tags(myservice):
    """Tests my service crud , edit tags and ownership

    Metadata:
        test_flag: provision
    """
    myservice.set_ownership("Administrator", "EvmGroup-administrator")
    myservice.edit_tags("Cost Center *", "Cost Center 001")
    with update(myservice):
        myservice.description = "my edited description"
    myservice.delete()


@pytest.mark.parametrize("filetype", ["Text", "CSV", "PDF"])
# PDF not present on upstream
@pytest.mark.uncollectif(lambda filetype: filetype == 'PDF' and not appliance_is_downstream())
def test_download_file(needs_firefox, myservice, filetype):
    """Tests my service download files

    Metadata:
        test_flag: provision
    """
    myservice.download_file(filetype)
