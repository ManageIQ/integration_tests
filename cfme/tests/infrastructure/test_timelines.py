import pytest

from cfme.base.ui import ServerDiagnosticsView
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for, TimedOutError
from cfme.markers.env_markers.provider import providers

all_infra_prov = ProviderFilter(classes=[InfraProvider])
excluded = ProviderFilter(classes=[SCVMMProvider, RHEVMProvider], inverted=True)
pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers, filters=[excluded, all_infra_prov], scope='module'),
    pytest.mark.usefixtures('setup_provider_modscope')
]


@pytest.fixture(scope='module')
def new_vm(request, provider):
    vm = VM.factory(random_vm_name('timelines', max_length=16), provider)
    logger.debug('Fixture new_vm set up! Name: %r', vm.name)
    logger.info('Will create  %r on Provider: %r', vm.name, vm.provider.name)
    vm.create_on_provider(find_in_cfme=False, timeout=500)
    yield vm
    vm.cleanup_on_provider()

@pytest.fixture(scope="module")
def mark_vm_as_appliance(new_vm, appliance):
    # set diagnostics vm
    relations_view = navigate_to(new_vm, 'EditManagementEngineRelationship')
    server_name = "{name} ({sid})".format(name=appliance.server.name, sid=appliance.server.sid)
    relations_view.form.server.select_by_visible_text(server_name)
    relations_view.form.save_button.click()


class VMEvent(object):
    """Class for generating  events on a VM in order to check it on Timelines.
    Args:
        vm: A VM object (Object)
        event: an event, Key in ACTIONS.(String)
    """
    ACTIONS = {
        'create': {
            'tl_event': ('VmDeployedEvent', 'USER_RUN_VM', 'USER_ADD_VM_FINISHED_SUCCESS'),
            'tl_category': 'Creation/Addition',
            'db_event_type': ('vm_create', 'USER_RUN_VM'),
            'emit_cmd': '_setup_vm'
        },
        'start': {
            'tl_event': ('VmPoweredOnEvent', 'USER_STARTED_VM'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_start',
            'emit_cmd': '_power_on'
        },
        'stop': {
            'tl_event': ('VmPoweredOffEvent', 'USER_STOP_VM'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_poweroff',
            'emit_cmd': '_power_off'
        },
        'suspend': {
            'tl_event': ('VmSuspendedEvent', 'USER_SUSPEND_VM'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_suspend',
            'emit_cmd': '_suspend'
        },
        'rename': {
            'tl_event': 'VmReconfiguredEvent',
            'tl_category': 'Configuration/Reconfiguration',
            'db_event_type': 'VmRenamedEvent',
            'emit_cmd': '_rename_vm'
        },
    }

    def __init__(self, vm, event):
        self.vm = vm
        self.event = event
        self.__dict__.update(self.ACTIONS[self.event])

    def emit(self):
        try:
            emit_action = getattr(self, self.emit_cmd)
            emit_action()
        except AttributeError:
            raise ValueError('{} is not a valid key in ACTION'.format(self.event))

    def _setup_vm(self):
        if not self.vm.provider.mgmt.does_vm_exist(self.vm.name):
            logger.info('Will set up the VM %r ton the provider', self.vm.name)
            return self.vm.create_on_provider(find_in_cfme=True)
        else:
            logger.info('%r already exists on the provider.', self.vm.name)

    def _power_on(self):
        return self.vm.provider.mgmt.start_vm(self.vm.name)

    def _power_off(self):
        return self.vm.provider.mgmt.stop_vm(self.vm.name)

    def _suspend(self):
        return self.vm.provider.mgmt.suspend_vm(self.vm.name)

    def _rename_vm(self):
        logger.info('%r will be renamed', self.vm.name)
        new_name = self.vm.provider.mgmt.rename_vm(self.vm.name, self.vm.name + '-renamed')
        logger.info('%r new name is %r', self.vm.name, new_name)
        self.vm.name = new_name
        self.vm.provider.mgmt.restart_vm(self.vm.name)
        return self.vm.name

    def _check_timelines(self, target):
        """Navigate to the TL of the given target, select the category of the event and verify
        that the tl_event of the VMEvent is present. if will return the length of the array
        containing  the events found in that timeline.


        Args:
            target: A entity where a Timeline is present ( VM, Host, Cluster...)

        Returns:
             The length of the array containing the event found on the Timeline of the target.
        """
        timelines_view = navigate_to(target, 'Timelines')

        if isinstance(timelines_view, ServerDiagnosticsView):
            timelines_view = timelines_view.timelines
            timeline_filter = timelines_view.filter
        else:
            timeline_filter = timelines_view.filter

        for selected_option in timeline_filter.event_category.all_selected_options:
            timeline_filter.event_category.select_by_visible_text(selected_option)

        timeline_filter.event_category.select_by_visible_text(self.tl_category)
        timeline_filter.time_position.select_by_visible_text('centered')
        timeline_filter.apply.click()
        events_list = timelines_view.chart.get_events(self.tl_category)
        logger.debug('events_list: ', events_list)
        logger.info('Searching for event type: %r in timeline category: %r', self.event,
                    self.tl_category)

        if not len(events_list):
            self.vm.provider.refresh_provider_relationships()
            logger.warn('Event list of %r is empty!', target)

        found_events = []

        for evt in events_list:
            if hasattr(evt, 'destination_vm'):
                #  Specially for the VmDeployedEvent where the source_vm defers from the
                # self.vm.name
                if evt.destination_vm == self.vm.name and evt.event_type in self.tl_event:
                    found_events.append(evt)
                    break
            elif not hasattr(evt, 'source_vm') or not hasattr(evt, 'source_host'):
                logger.warn('Event %r does not have source_vm, source_host. Probably an issue', evt)
            elif evt.source_vm == self.vm.name and evt.event_type in self.tl_event:
                found_events.append(evt)
                break

        logger.info('found events on {tgt}: {evt}'.format(tgt=target, evt="\n".join([repr(e) for e
                                                                                    in
                                                                    found_events])))
        return len(found_events)

    def catch_in_timelines(self, soft_assert, targets):
        if targets:
            for target in targets:
                try:
                    wait_for(self._check_timelines, [target], timeout='5m', fail_condition=0)
                except TimedOutError:
                    soft_assert(False, '0 occurrence of {} found on the timeline of {}'.format(
                        self.event, target))
        else:
            raise ValueError('Targets must not be empty')


@pytest.mark.rhv2
def test_timeline_events(new_vm, soft_assert):
    events_list = ['create', 'stop', 'start', 'suspend', 'start']
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    for event in events_list:
        vm_event = VMEvent(new_vm, event)
        logger.info('Will generate event %r on machine %r', event, new_vm.name)
        wait_for(vm_event.emit, timeout='5m', message='Event {} did timeout'.format(event))
        vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_diagnostic_timeline_events(new_vm, soft_assert, mark_vm_as_appliance):
    events_list = ['create']
    targets = (new_vm.appliance.server,)
    for event in events_list:
        logger.info('Will generate event %r on machine %r', event, new_vm.name)
        vm_event = VMEvent(new_vm, event)
        vm_event.catch_in_timelines(soft_assert, targets)
