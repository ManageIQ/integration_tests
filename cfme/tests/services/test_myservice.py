# -*- coding: utf-8 -*-
from datetime import datetime

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.services.myservice.ui import MyServiceDetailView
from cfme.utils import browser
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.browser import ensure_browser_open
from cfme.utils.update import update
from cfme.utils.wait import wait_for

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


@pytest.mark.parametrize('context', [ViaUI])
def test_retire_service_ui(appliance, context, service_vm):
    """Tests my service

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service, _ = service_vm
    with appliance.context.use(context):
        service.retire()


@pytest.mark.parametrize('context', [ViaUI])
def test_retire_service_on_date(appliance, context, service_vm):
    """Tests my service retirement

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service, _ = service_vm
    with appliance.context.use(context):
        dt = datetime.utcnow()
        service.retire_on_date(dt)


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.meta(blockers=[BZ(1729940)])
def test_crud_set_ownership_and_edit_tags(appliance, context, service_vm):
    """Tests my service crud , edit tags and ownership

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """

    service, _ = service_vm
    with appliance.context.use(context):
        service.set_ownership("Administrator", "EvmGroup-administrator")
        service.add_tag()
        with update(service):
            service.description = "my edited description"
        service.delete()


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.parametrize("filetype", ["Text", "CSV", "PDF"])
# PDF not present on upstream
@pytest.mark.uncollectif(lambda appliance, filetype:
                         filetype == 'PDF' and not appliance.is_downstream,
                         reason='PDF downloads not supported on upstream')
def test_download_file(appliance, context, needs_firefox, service_vm, filetype):
    """Tests my service download files

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        tags: service
    """
    service, _ = service_vm
    with appliance.context.use(context):
        service.download_file(filetype)


@pytest.mark.parametrize('context', [ViaUI])
def test_service_link(appliance, context, service_vm):
    """Tests service link from VM details page(BZ1443772)

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """
    service, vm = service_vm
    with appliance.context.use(context):
        # TODO: Update to nav to MyService first to click entity link when widget exists
        view = navigate_to(vm, 'Details')
        view.entities.summary('Relationships').click_at('Service')
        new_view = service.create_view(MyServiceDetailView)
        assert new_view.wait_displayed()


@pytest.mark.parametrize('context', [ViaUI])
@pytest.mark.meta(automates=[BZ(1720338)])
def test_retire_service_with_retired_vm(appliance, context, service_vm):
    """Tests retire service with an already retired vm.

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service

    Bugzilla:
        1720338
    """
    service, vm = service_vm
    vm.retire()
    # using rest entity to check if the VM has retired since it is a lot faster
    retire_vm = appliance.rest_api.collections.vms.get(name=vm.name)
    wait_for(
        lambda: (hasattr(retire_vm, "retired") and retire_vm.retired),
        timeout=1000,
        delay=5,
        fail_func=retire_vm.reload,
    )
    with appliance.context.use(context):
        service.retire()


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
@pytest.mark.ignore_stream('5.10')
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


@pytest.mark.meta(coverage=[1727443])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_service_load():
    """
    Bugzilla:
        1727443
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.11
        testSteps:
            1. Create catalog and catalog item
            2. Order the catalog item
            3. Make 1k copy of above service
            4. Go to My services
        expectedResults:
            1.
            2.
            3.
            4. Tree should load faster when having 1000+ services
    """
    pass


@pytest.mark.meta(coverage=[1722194])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_retire_multiple_services():
    """
    Bugzilla:
        1722194
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.11
        testSteps:
            1. Create catalog and create two catalog item
            2. Order the catalog items
            3. Go to My services
            4. Retire the both services
        expectedResults:
            1.
            2.
            3.
            4. Services should retire and vms as well
    """
    pass


@pytest.mark.meta(coverage=[1718102, 1718898, 1741327])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_load_multiple_services():
    """
    Bugzilla:
        1718102

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.10
        testSteps:
            1. Create catalog and catalog item
            2. Order the catalog items
            3. create 999 services from rails "999.times {Service.first.dup.save}"
            4. Go to My services
            5. Refresh the page and load the 1000 services
        expectedResults:
            1.
            2.
            3.
            4.
            5. The page should load in less than 10 seconds
    """
    pass


@pytest.mark.meta(coverage=[1737559])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_load_service_with_button():
    """
    Bugzilla:
        1737559

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.10
        testSteps:
            1. Import Datastore and dialog
            2. Create button with above dialog
            3. Create catalog item
            4. Order the service
            5. Go to My services
            6. Click on created service
            7. load the service with a button
        expectedResults:
            1.
            2.
            3.
            4.
            5.
            6.
            7. Service should load without an error in log
    """
    pass
