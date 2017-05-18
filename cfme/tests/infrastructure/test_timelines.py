# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from utils import version, testgen
from utils.appliance.implementations.ui import navigate_to
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for


pytestmark = [pytest.mark.tier(2), pytest.mark.usefixtures("setup_provider_modscope")]
pytest_generate_tests = testgen.generate([InfraProvider], scope='module')


@pytest.yield_fixture(scope='session')
def new_vm(provider):
    logger.warn('new_vm setup')
    vm = VM.factory(random_vm_name("timelines", max_length=16), provider)
    yield vm

    logger.warn('new_vm teardown')


class VMEvent(object):
    def __init__(self, vm, event):
        self.vm = vm

        self.action = event
        if self.action == 'create':
            self.tl_event = 'VmDeployedEvent'
            self.tl_category = 'Creation/Addition'
            self.db_event = ''
            self.emit_cmd = lambda: self.vm.create_on_provider(allow_skip="default",
                                                               find_in_cfme=True)
        elif self.action == 'stop':
            self.tl_event = 'VmPoweredOffEvent'
            self.tl_category = 'Power Activity'
            self.db_event = ''
            self.emit_cmd = lambda: self.vm.provider.mgmt.stop_vm(self.vm.name)
        elif self.action == ('start', 'resume'):
            self.tl_event = 'VmPoweredOnEvent'
            self.tl_category = 'Power Activity'
            self.db_event = ''
            self.emit_cmd = lambda: self.vm.provider.mgmt.start_vm(self.vm.name)
        elif self.action == 'suspend':
            self.tl_event = 'VmSuspendedEvent'
            self.tl_category = 'Power Activity'
            self.db_event = ''
            self.emit_cmd = lambda: self.vm.provider.mgmt.suspend_vm(self.vm.name)
        elif self.action == 'delete':
            self.tl_event = 'VmRemovedEvent'
            self.tl_category = 'Deletion/Removal'
            self.db_event = ''
            self.emit_cmd = lambda: self.vm.provider.mgmt.delete_vm(self.vm.name)

    def emit(self):
        self.emit_cmd()

    def catch_in_timelines(self):
        for target in (self.vm, self.vm.host, self.vm.cluster, self.vm.provider):
            wait_for(self._check_timelines, [target], timeout='5m', fail_condition=0,
                     message="events to appear")

    def _check_timelines(self, target):
        timelines_view = navigate_to(target, 'Timelines')
        timelines_view.filter.time_position.select_by_visible_text('centered')
        timelines_view.filter.apply.click()
        found_events = []
        for evt in timelines_view.chart.get_events():
            if not hasattr(evt, 'source_vm'):
                # BZ(1428797)
                logger.warn(
                    "event {evt} doesn't have source_vm field. Probably issue".format(evt=evt))
                continue
            elif evt.source_vm == self.vm.name and evt.event_type == self.tl_event:
                found_events.append(evt)

        logger.info("found events: {evt}".format(evt="\n".join([repr(e) for e in found_events])))
        return len(found_events)

    def catch_in_db(self):
        pass


@pytest.mark.parametrize('vm_event', ['create', 'stop', 'start', 'suspend', 'resume', 'delete'], ids=['create', 'stop', 'start', 'suspend', 'resume', 'delete'])
def test_event(vm_event, new_vm):
    # event = VMEvent(vm=new_vm, event=vm_event)
    # gen event
    # event.emit()
    # check event in db
    # event.catch_in_db()
    # check vm/host/cluster/provider timelines
    # event.catch_in_timelines()
    logger.warn(new_vm.name)
    pass


def test_event_blabla(new_vm):
    # event = VMEvent(vm=new_vm, event=vm_event)
    # gen event
    # event.emit()
    # check event in db
    # event.catch_in_db()
    # check vm/host/cluster/provider timelines
    # event.catch_in_timelines()
    logger.warn(new_vm.name)
    pass


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
