# -*- coding: utf-8 -*-
from datetime import datetime

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.myservice import MyService
from cfme.services.myservice.ui import MyServiceDetailView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import browser
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.browser import ensure_browser_open
from cfme.utils.log import logger
from cfme.utils.update import update
from cfme.utils.version import appliance_is_downstream

pytestmark = [
    pytest.mark.usefixtures('setup_provider', 'catalog_item'),
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
]


@pytest.fixture
def needs_firefox():
    """ Fixture which skips the test if not run under firefox.

    I recommend putting it in the first place.
    """
    ensure_browser_open()
    if browser.browser().name != "firefox":
        pytest.skip(msg="This test needs firefox to run")


@pytest.fixture(scope='function')
def myservice(appliance, provider, catalog_item, request):
    """Tests my service

    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.prov_data["catalog"]["vm_name"] + '0001'
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    request_description = catalog_item.name
    service_request = appliance.collections.requests.instantiate(request_description,
                                                                 partial_check=True)
    service_request.wait_for_request()
    assert service_request.is_succeeded(),\
        ("Request failed with the message {}".format(service_request.rest.message))

    yield catalog_item.name, vm_name

    appliance.collections.infra_vms.instantiate(vm_name, provider).cleanup_on_provider()


@pytest.mark.parametrize('context', [ViaUI])
def test_retire_service_ui(appliance, context, myservice):
    """Tests my service

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
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

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
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

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """

    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        myservice.set_ownership("Administrator", "EvmGroup-administrator")
        myservice.add_tag()
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

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        tags: service
    """
    service_name, vm_name = myservice
    with appliance.context.use(context):
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        myservice.download_file(filetype)


@pytest.mark.parametrize('context', [ViaUI])
def test_service_link(appliance, context, myservice, provider):
    """Tests service link from VM details page(BZ1443772)

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service_name, vm_name = myservice
    with appliance.context.use(context):
        # TODO: Update to nav to MyService first to click entity link when widget exists
        myservice = MyService(appliance, name=service_name, vm_name=vm_name)
        vm = appliance.provider_based_collection(coll_type='vms', provider=provider).instantiate(
            name=myservice.vm_name,
            provider=provider
        )
        view = navigate_to(vm, 'Details')
        view.entities.summary('Relationships').click_at('Service')
        new_view = myservice.create_view(MyServiceDetailView)
        assert new_view.wait_displayed()


@pytest.mark.manual
@pytest.mark.tier(3)
def test_retire_on_date_for_multiple_service():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
    """
    pass


@pytest.mark.meta(coverage=[1678123])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_service_state():
    """
    Bugzilla:
        1678123
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Create catalog and catalog item
            2. Order the catalog item
            3. Provision the service catalog item or fail the service catalog item
            4. Go to My services and check service state
        expectedResults:
            1.
            2.
            3.
            4. Service State should be Provisioned or Failed
    """
    pass
