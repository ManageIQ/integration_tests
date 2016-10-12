# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.rest import a_provider as _a_provider
from cfme.rest import vm as _vm
from cfme.web_ui import InfoBlock, toolbar, jstimelines
from cfme.exceptions import ToolbarOptionGreyedOrUnavailable
from utils import testgen
from utils import version
from utils.log import logger
from utils.wait import wait_for
from selenium.common.exceptions import NoSuchElementException
from utils.appliance.endpoints.ui import navigate_to


pytestmark = [pytest.mark.tier(2)]


@pytest.fixture(scope="module")
def delete_fx_provider_event(db, provider):
    logger.debug("Deleting timeline events for provider name %s", provider.name)
    ems = db['ext_management_systems']
    ems_events_table_name = version.pick({version.LOWEST: 'ems_events', '5.5': 'event_streams'})
    ems_events = db[ems_events_table_name]
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider.name)
        )
        db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery())).delete(False)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter', 'rhevm'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def vm_name():
    # We have to use "tt" here to avoid name truncating in the timelines view
    return "test_tt_" + fauxfactory.gen_alphanumeric(length=4)


@pytest.fixture(scope="module")
def test_vm(request, provider, vm_name, setup_provider_modscope):
    """Fixture to provision appliance to the provider being tested if necessary"""
    navigate_to(InfraProvider, 'All')
    vm = VM.factory(vm_name, provider)

    request.addfinalizer(vm.delete_from_provider)

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        vm.refresh_relationships()
    return vm


@pytest.fixture(scope="module")
def gen_events(delete_fx_provider_event, provider, test_vm):
    logger.debug('Starting, stopping VM')
    mgmt = provider.mgmt
    mgmt.stop_vm(test_vm.name)
    mgmt.start_vm(test_vm.name)


def count_events(vm, nav_step):
    try:
        nav_step()
    except ToolbarOptionGreyedOrUnavailable:
        return 0
    except NoSuchElementException:
        vm.rediscover()
        return 0

    events = []
    for event in jstimelines.events():
        data = event.block_info()
        if vm.name in data.values():
            events.append(event)
            if len(events) > 0:
                return len(events)
    return 0


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1264183, 1281746])
def test_provider_event(provider, gen_events, test_vm):
    """Tests provider event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        pytest.sel.force_navigate('infrastructure_provider',
                                  context={'provider': provider})
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_vm, nav_step], timeout='5m', fail_condition=0,
             message="events to appear")


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1281746])
def test_host_event(provider, gen_events, test_vm):
    """Tests host event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_vm.load_details()
        pytest.sel.click(InfoBlock.element('Relationships', 'Host'))
        toolbar.select('Monitoring', 'Timelines')

    wait_for(count_events, [test_vm, nav_step], timeout='10m', fail_condition=0,
             message="events to appear")


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1281746])
def test_vm_event(provider, gen_events, test_vm):
    """Tests vm event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_vm.load_details()
        toolbar.select('Monitoring', 'Timelines')

    wait_for(count_events, [test_vm, nav_step], timeout='3m', fail_condition=0,
             message="events to appear")


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[1281746])
def test_cluster_event(provider, gen_events, test_vm):
    """Tests cluster event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        # fixme: sometimes get_clusters doesn't return all found clusters
        # fixme: this try/except statement tries to avoid this
        all_clusters = []
        try:
            all_clusters = provider.get_clusters()
            cluster = [cl for cl in all_clusters if cl.id == test_vm.cluster_id][-1]
            navigate_to(cluster, 'Details')
            toolbar.select('Monitoring', 'Timelines')
        except IndexError:
            logger.error("the following clusters were "
                         "found for provider {p}: {cl} ".format(p=provider.name, cl=all_clusters))
    wait_for(count_events, [test_vm, nav_step], timeout='5m',
             fail_condition=0, message="events to appear")


class TestVmEventRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self):
        return _a_provider()

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, rest_api_modscope):
        return _vm(request, a_provider, rest_api_modscope)

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_vm_add_event(self, rest_api, vm, db, from_detail):
        event = {
            "event_type": "BadUserNameSessionEvent",
            "event_message": "Cannot login user@test.domain {}".format(from_detail)
        }
        rest_vm = rest_api.collections.vms.get(name=vm)
        if from_detail:
            assert rest_vm.action.add_event(**event)["success"], "Could not add event"
        else:
            response = rest_api.collections.vms.action.add_event(rest_vm, **event)
            assert len(response) > 0, "Could not add event"

        # DB check, doesn't work on 5.4
        if version.current_version() < '5.5':
            return True
        events = db["event_streams"]
        events_list = list(db.session.query(events).filter(
            events.vm_name == vm,
            events.message == event["event_message"],
            events.event_type == event["event_type"],
        ))
        assert len(events_list) == 1, "Could not find the event in the database"

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_vm_add_lifecycle_event(self, request, rest_api, vm, from_detail, db):
        """Test that checks whether adding a lifecycle event using the REST API works.
        Prerequisities:
            * A VM
        Steps:
            * Find the VM's id
            * Prepare the lifecycle event data (``status``, ``message``, ``event``)
            * Call either:
                * POST /api/vms/<id> (method ``add_lifecycle_event``) <- the lifecycle data
                * POST /api/vms (method ``add_lifecycle_event``) <- the lifecycle data
                    and resources field specifying list of dicts containing hrefs to the VMs,
                    in this case only one.
            * Verify that appliance's database contains such entries in table ``lifecycle_events``
        Metadata:
            test_flag: rest
        """
        if "add_lifecycle_event" not in rest_api.collections.vms.action.all:
            pytest.skip("add_lifecycle_event action is not implemented in this version")
        rest_vm = rest_api.collections.vms.get(name=vm)
        event = dict(
            status=fauxfactory.gen_alphanumeric(),
            message=fauxfactory.gen_alphanumeric(),
            event=fauxfactory.gen_alphanumeric(),
        )
        if from_detail:
            assert rest_vm.action.add_lifecycle_event(**event)["success"], "Could not add event"
        else:
            assert len(rest_api.collections.vms.action.add_lifecycle_event(rest_vm, **event)) > 0,\
                "Could not add event"
        # DB check
        lifecycle_events = db["lifecycle_events"]
        assert len(list(db.session.query(lifecycle_events).filter(
            lifecycle_events.message == event["message"],
            lifecycle_events.status == event["status"],
            lifecycle_events.event == event["event"],
        ))) == 1, "Could not find the lifecycle event in the database"
