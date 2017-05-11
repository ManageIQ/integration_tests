# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM

from cfme.infrastructure.host import Host
from cfme.infrastructure.provider import InfraProvider
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from cfme.web_ui import InfoBlock
from utils import version, testgen
from utils.appliance.implementations.ui import navigate_to
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for


pytestmark = [pytest.mark.tier(2),
              pytest.mark.usefixtures("setup_provider_modscope")]
pytest_generate_tests = testgen.generate([InfraProvider], scope='module')


@pytest.fixture(scope="module")
def test_vm(request, provider):
    vm = VM.factory(random_vm_name("timelines", max_length=16), provider)

    request.addfinalizer(vm.delete_from_provider)

    if not provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, provider.key)
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
    found_events = []
    for evt in timelines_view.chart.get_events():
        if not hasattr(evt, 'source_vm'):
            # BZ(1428797)
            logger.warn("event {evt} doesn't have source_vm field. Probably issue".format(evt=evt))
            continue
        elif evt.source_vm == vm.name:
            found_events.append(evt)

    logger.info("found events: {evt}".format(evt="\n".join([repr(e) for e in found_events])))
    return len(found_events)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_provider_event(gen_events, test_vm):
    """Tests provider event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [test_vm.provider, test_vm], timeout='5m', fail_condition=0,
             message="events to appear")


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_vm_event(gen_events, test_vm):
    """Tests vm event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [test_vm, test_vm], timeout='3m', fail_condition=0,
             message="events to appear")


@pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
def test_cluster_event(gen_events, test_vm):
    """Tests cluster event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    all_clusters = test_vm.provider.get_clusters()
    cluster = next(cl for cl in all_clusters if cl.id == test_vm.cluster_id)
    wait_for(count_events, [cluster, test_vm], timeout='5m',
             fail_condition=0, message="events to appear")


class TestVmEventRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self, request):
        return _a_provider(request)

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, appliance):
        return _vm(request, a_provider, appliance.rest_api)

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_vm_add_event(self, vm, from_detail, appliance):
        """Test that checks whether adding a event using the REST API works.
        Prerequisities:
            * A VM
        Steps:
            * Find the VM's id
            * Prepare the event data
            * Call either:
                * POST /api/vms/<id> (method ``add_event``) <- the event data
                * POST /api/vms (method ``add_lifecycle_event``) <- the event data
                    and resources field specifying list of dicts containing hrefs to the VMs,
                    in this case only one.
            * Verify that appliance's database contains such entries in table ``event_streams``
        Metadata:
            test_flag: rest
        """
        event = {
            "event_type": "BadUserNameSessionEvent",
            "event_message": "Cannot login user@test.domain {}".format(from_detail)
        }
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)
        if from_detail:
            responses = [rest_vm.action.add_event(**event)]
        else:
            responses = appliance.rest_api.collections.vms.action.add_event(rest_vm, **event)
        assert appliance.rest_api.response.status_code == 200
        for response in responses:
            assert response["success"] is True, "Could not add event"

        events = appliance.db["event_streams"]
        events_list = list(appliance.db.session.query(events).filter(
            events.vm_name == vm,
            events.message == event["event_message"],
            events.event_type == event["event_type"],
        ))
        assert events_list, "Could not find the event in the database"

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_vm_add_lifecycle_event(self, vm, from_detail, appliance):
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
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)
        event = dict(
            status=fauxfactory.gen_alphanumeric(),
            message=fauxfactory.gen_alphanumeric(),
            event=fauxfactory.gen_alphanumeric(),
        )
        if from_detail:
            responses = [rest_vm.action.add_lifecycle_event(**event)]
        else:
            responses = appliance.rest_api.collections.vms.action.add_lifecycle_event(
                rest_vm, **event)
        assert appliance.rest_api.response.status_code == 200
        for response in responses:
            assert response["success"] is True, "Could not add event"

        # DB check
        lifecycle_events = appliance.db["lifecycle_events"]
        events_list = list(appliance.db.session.query(lifecycle_events).filter(
            lifecycle_events.message == event["message"],
            lifecycle_events.status == event["status"],
            lifecycle_events.event == event["event"],
        ))
        assert events_list, "Could not find the lifecycle event in the database"
