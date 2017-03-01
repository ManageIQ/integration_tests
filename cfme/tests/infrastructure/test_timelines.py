# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM

from cfme.infrastructure.host import  Host
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from cfme.web_ui import InfoBlock, toolbar, jstimelines
from utils import version
from utils.log import logger
from utils.providers import setup_a_provider, ProviderFilter
from utils.wait import wait_for
from utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(2)]


@pytest.fixture(scope="module")
def a_provider():
    try:
        pf = ProviderFilter(classes=[VMwareProvider, RHEVMProvider])
        return setup_a_provider(filters=[pf])
    except Exception:
        pytest.skip("It's not possible to set up any providers, therefore skipping")


@pytest.fixture(scope="module")
def test_vm(request, a_provider):
    vm_name = "test_tl_" + fauxfactory.gen_alphanumeric(length=4)
    vm = VM.factory(vm_name, a_provider)

    request.addfinalizer(vm.delete_from_provider)

    if not a_provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, a_provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    return vm


@pytest.fixture(scope="module")
def gen_events(test_vm):
    logger.debug('Starting, stopping VM')
    mgmt = test_vm.provider.mgmt
    mgmt.stop_vm(test_vm.name)
    mgmt.start_vm(test_vm.name)


def count_events(target, vm):
    timelines_view = navigate_to(target, 'Timelines')
    timelines_view.filter.time_position.select_by_visible_text('centered')
    timelines_view.filter.apply.click()
    events = [evt for evt in timelines_view.chart.get_events() if evt.source_vm == vm.name]
    logger.info("found events: {evt}".format(evt="\n".join(events)))
    return len(events)


@pytest.mark.meta(blockers=[1264183, 1281746])
def test_provider_event(gen_events, test_vm):
    """Tests provider event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [test_vm.provider, test_vm], timeout='5m', fail_condition=0,
             message="events to appear")


@pytest.mark.meta(blockers=[1281746])
def test_host_event(gen_events, test_vm):
    """Tests host event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    test_vm.load_details()
    host_name = InfoBlock.text('Relationships', 'Host')
    host = Host(name=host_name, provider=test_vm.provider)
    wait_for(count_events, [host, test_vm], timeout='10m', fail_condition=0,
             message="events to appear")


@pytest.mark.meta(blockers=[1281746])
def test_vm_event(gen_events, test_vm):
    """Tests vm event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [test_vm, test_vm], timeout='3m', fail_condition=0,
             message="events to appear")


@pytest.mark.meta(blockers=[1281746])
def test_cluster_event(gen_events, test_vm):
    """Tests cluster event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    # fixme: sometimes get_clusters doesn't return clusters
    all_clusters = test_vm.provider.get_clusters()
    cluster = next(cl for cl in all_clusters if cl.id == test_vm.cluster_id)
    wait_for(count_events, [cluster, test_vm], timeout='5m',
             fail_condition=0, message="events to appear")


class TestVmEventRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self, request):
        return _a_provider(request)

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
