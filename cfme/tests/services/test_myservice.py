# -*- coding: utf-8 -*-
import pytest
from datetime import datetime

from cfme import test_requirements
from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.services.myservice.ui import MyServiceDetailView

from cfme.utils import browser, testgen, version
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import ensure_browser_open
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.version import appliance_is_downstream
from cfme.utils.appliance import ViaUI


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
def myservice(appliance, setup_provider, provider, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = version.pick({
        version.LOWEST: catalog_item.provisioning_data["catalog"]["vm_name"] + '_0001',
        '5.7': catalog_item.provisioning_data["catalog"]["vm_name"] + '0001'})
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(request_description,
                                                                 partial_check=True)
    service_request.wait_for_request()
    assert service_request.is_succeeded()

    yield catalog_item.name, vm_name

    cleanup_vm(vm_name, provider)


@pytest.mark.parametrize('context', [ViaUI])
def test_retire_service(appliance, context, myservice):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        myservice.retire()


@pytest.mark.parametrize('context', [ViaUI])
def test_retire_service_on_date(appliance, context, myservice):
    """Tests my service retirement

    Metadata:
        test_flag: provision
    """
    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        dt = datetime.utcnow()
        myservice.retire_on_date(dt)


@pytest.mark.parametrize('context', [ViaUI])
def test_crud_set_ownership_and_edit_tags(appliance, context, myservice):
    """Tests my service crud , edit tags and ownership

    Metadata:
        test_flag: provision
    """

    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        myservice.set_ownership("Administrator", "EvmGroup-administrator")
        myservice.add_tag("Cost Center *", "Cost Center 001")
        with update(myservice):
            myservice.description = "my edited description"
        myservice.delete()


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.parametrize("filetype", ["Text", "CSV", "PDF"])
# PDF not present on upstream
@pytest.mark.uncollectif(lambda filetype: filetype == 'PDF' and not appliance_is_downstream())
def test_download_file(appliance, context, needs_firefox, myservice, filetype):
    """Tests my service download files

    Metadata:
        test_flag: provision
    """
    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        myservice.download_file(filetype)


@pytest.mark.parametrize('context', [ViaUI])
def test_service_link(appliance, context, myservice):
    """Tests service link from VM details page(BZ1443772)"""
    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        view = navigate_to(myservice, 'VMDetails')
        view.relationships.click_at("Service")
        new_view = myservice.create_view(MyServiceDetailView)
        assert new_view.is_displayed
