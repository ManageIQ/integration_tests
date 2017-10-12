# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.base.ui import Server
from cfme.common.provider import BaseProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for
from fixtures.provider import setup_one_or_skip


pytestmark = [pytest.mark.tier(2)]


@pytest.fixture(scope='module')
def a_provider(request):
    BaseProvider.clear_providers()
    not_scvmm = ProviderFilter(classes=[SCVMMProvider],
                               inverted=True)  # scvmm doesn't provide events
    all_prov = ProviderFilter(classes=[InfraProvider])
    return setup_one_or_skip(request, filters=[not_scvmm, all_prov])


@pytest.fixture(scope="module")
def new_vm(request, a_provider):
    vm = VM.factory(random_vm_name("timelines", max_length=16), a_provider)

    request.addfinalizer(vm.delete_from_provider)

    if not a_provider.mgmt.does_vm_exist(vm.name):
        logger.info("deploying %s on provider %s", vm.name, a_provider.key)
        vm.create_on_provider(allow_skip="default", find_in_cfme=True)
    return vm


@pytest.yield_fixture(scope="module")
def mark_vm_as_appliance(new_vm, appliance):
    # set diagnostics vm
    relations_view = navigate_to(new_vm, 'EditManagementEngineRelationship')
    server_name = "{name} ({sid})".format(name=appliance.server.name, sid=appliance.server.sid)
    relations_view.form.server.select_by_visible_text(server_name)
    relations_view.form.save_button.click()
    yield
    # unset diagnostics vm
    relations_view = navigate_to(new_vm, 'EditManagementEngineRelationship')
    relations_view.form.server.select_by_visible_text('<Not a Server>')
    relations_view.form.save_button.click()


@pytest.fixture(scope="module")
def gen_events(new_vm):
    logger.debug('Starting, stopping VM')
    mgmt = new_vm.provider.mgmt
    mgmt.stop_vm(new_vm.name)
    mgmt.start_vm(new_vm.name)


def count_events(target, vm):
    timelines_view = navigate_to(target, 'Timelines')
    if isinstance(target, Server):
        timelines_view = timelines_view.timelines
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


def test_infra_provider_event(gen_events, new_vm):
    """Tests provider event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [new_vm.provider, new_vm], timeout='5m', fail_condition=0,
             message="events to appear")


def test_infra_host_event(appliance, a_provider, gen_events, new_vm):
    """Tests host event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    view = navigate_to(new_vm, "Details")
    host_name = view.entities.relationships.get_text_of('Host')
    host_collection = appliance.collections.hosts
    host = host_collection.instantiate(name=host_name, provider=a_provider)
    wait_for(count_events, [host, new_vm], timeout='10m', fail_condition=0,
             message="events to appear")


def test_infra_vm_event(gen_events, new_vm):
    """Tests vm event on timelines

    Metadata:
        test_flag: timelines, provision
    """

    wait_for(count_events, [new_vm, new_vm], timeout='3m', fail_condition=0,
             message="events to appear")


def test_infra_cluster_event(gen_events, new_vm):
    """Tests cluster event on timelines

    Metadata:
        test_flag: timelines, provision
    """
    all_clusters = new_vm.provider.get_clusters()
    cluster = next(cl for cl in all_clusters if cl.id == new_vm.cluster_id)
    wait_for(count_events, [cluster, new_vm], timeout='5m',
             fail_condition=0, message="events to appear")


@pytest.mark.meta(blockers=[BZ(1429962, forced_streams=["5.7"])])
def test_infra_vm_diagnostic_timelines(gen_events, new_vm, mark_vm_as_appliance, appliance):
    """Tests timelines on settings->diagnostics page

    Metadata:
        test_flag: timelines, provision
    """
    # go diagnostic timelines
    wait_for(count_events, [appliance.server, new_vm], timeout='5m',
             fail_condition=0, message="events to appear")


class TestInfraVmEventRESTAPI(object):
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

        events = appliance.db.client["event_streams"]
        events_list = list(appliance.db.client.session.query(events).filter(
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
        lifecycle_events = appliance.db.client["lifecycle_events"]
        events_list = list(appliance.db.client.session.query(lifecycle_events).filter(
            lifecycle_events.message == event["message"],
            lifecycle_events.status == event["status"],
            lifecycle_events.event == event["event"],
        ))
        assert events_list, "Could not find the lifecycle event in the database"


@pytest.mark.manual
def test_policy_events():
    pass


@pytest.mark.manual
def test_timelines_ui():
    pass
