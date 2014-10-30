import pytest

from cfme.infrastructure.virtual_machines import Vm, details_page
from cfme.infrastructure.provider import prov_timeline
from cfme.web_ui import toolbar
from cfme.exceptions import ToolbarOptionGreyed
from utils import testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string
from utils.wait import wait_for

pytestmark = [pytest.mark.ignore_stream("upstream")]


@pytest.fixture(scope="module")
def delete_fx_provider_event(db, provider_crud):
    logger.debug("Deleting timeline events for provider name {}".format(provider_crud.name))
    ems = db['ext_management_systems']
    ems_events = db['ems_events']
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider_crud.name)
        )
        db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery())).delete(False)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def provider_init(provider_key):
    """cfme/infrastructure/provider.py provider object."""
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="module")
def vm_name():
    return "test_tt_" + generate_random_string(size=4)


@pytest.fixture(scope="module")
def test_vm(request, provider_crud, provider_mgmt, vm_name, provider_init):
    """Fixture to provision appliance to the provider being tested if necessary"""
    pytest.sel.force_navigate('infrastructure_providers')
    vm = Vm(vm_name, provider_crud)

    request.addfinalizer(vm.delete_from_provider)

    if not provider_mgmt.does_vm_exist(vm_name):
        vm.create_on_provider()
    return vm


@pytest.fixture(scope="module")
def gen_events(delete_fx_provider_event, provider_crud, test_vm):
    logger.debug('Starting, stopping VM')
    mgmt = provider_crud.get_mgmt_system()
    mgmt.stop_vm(test_vm.name)
    mgmt.start_vm(test_vm.name)


def count_events(vm_name, nav_step):
    try:
        nav_step()
    except ToolbarOptionGreyed:
        return 0
    events = []
    for event in prov_timeline.events():
        if event.text == vm_name:
            events.append(event)
    return len(events)


def test_provider_event(provider_crud, gen_events, test_vm):
    def nav_step():
        pytest.sel.force_navigate('infrastructure_provider',
                                  context={'provider': provider_crud})
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_vm.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


def test_host_event(provider_crud, gen_events, test_vm):
    def nav_step():
        test_vm.load_details()
        pytest.sel.click(details_page.infoblock.element('Relationships', 'Host'))
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_vm.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


def test_vm_event(provider_crud, gen_events, test_vm):
    def nav_step():
        test_vm.load_details()
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_vm.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


def test_cluster_event(provider_crud, gen_events, test_vm):
    def nav_step():
        test_vm.load_details()
        pytest.sel.click(details_page.infoblock.element('Relationships', 'Cluster'))
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_vm.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")
