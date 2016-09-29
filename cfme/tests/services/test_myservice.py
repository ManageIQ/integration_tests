# -*- coding: utf-8 -*-
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.catalogs.myservice import MyService
from cfme.services import requests
from cfme import test_requirements
from datetime import datetime
from utils import testgen
from utils.log import logger
from utils.wait import wait_for
from utils import browser
from utils.version import current_version
from utils.browser import ensure_browser_open

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


pytest_generate_tests = testgen.generate(testgen.provider_by_type, ['virtualcenter'],
    scope="module")


@pytest.fixture
def myservice(setup_provider, provider, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"] + "_0001"
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=2000, delay=20)
    assert row.last_message.text == 'Request complete'
    return MyService(catalog_item.name, vm_name)


def test_retire_service(provider, myservice, register_event):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    myservice.retire()
    register_event('Service', myservice.service_name, 'service_retired')


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
    myservice.update("edited", "edited_desc")
    edited_name = myservice.service_name + "_" + "edited"
    myservice.delete(edited_name)


@pytest.mark.uncollectif(lambda: current_version() < "5.5")
@pytest.mark.parametrize("filetype", ["Text", "CSV", "PDF"])
def test_download_file(needs_firefox, myservice, filetype):
    """Tests my service download files

    Metadata:
        test_flag: provision
    """
    myservice.download_file(filetype)
