import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.ui import ServerDiagnosticsView
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.kubevirt import KubeVirtProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

all_infra_prov = ProviderFilter(classes=[InfraProvider])
# SCVMM timelines are not supported per the support matrix, KubeVirt also should not be collected
excluded = ProviderFilter(classes=[SCVMMProvider, KubeVirtProvider], inverted=True)
pytestmark = [
    pytest.mark.tier(2),
    pytest.mark.provider(gen_func=providers, filters=[excluded, all_infra_prov]),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.timelines,
    test_requirements.events,
]


@pytest.fixture()
def new_vm(provider):
    vm = provider.appliance.collections.infra_vms.instantiate(
        random_vm_name('timelines', max_length=16), provider
    )
    vm.create_on_provider(find_in_cfme=True)
    logger.debug('Fixture new_vm set up! Name: %r Provider: %r', vm.name, vm.provider.name)
    yield vm
    vm.cleanup_on_provider()


@pytest.fixture()
def mark_vm_as_appliance(new_vm, appliance):
    # set diagnostics vm
    relations_view = navigate_to(new_vm, 'EditManagementEngineRelationship', wait_for_view=0)
    server_name = "{name} ({sid})".format(name=appliance.server.name, sid=appliance.server.sid)
    relations_view.form.server.select_by_visible_text(server_name)
    relations_view.form.save_button.click()


@pytest.fixture()
def control_policy(appliance, new_vm):
    action = appliance.collections.actions.create(fauxfactory.gen_alpha(), "Tag",
        dict(tag=("My Company Tags", "Environment", "Development")))
    policy = appliance.collections.policies.create(VMControlPolicy, fauxfactory.gen_alpha())
    policy.assign_events("VM Power Off")
    policy.assign_actions_to_event("VM Power Off", action)
    profile = appliance.collections.policy_profiles.create(fauxfactory.gen_alpha(),
                                                           policies=[policy])

    yield new_vm.assign_policy_profiles(profile.description)
    if profile.exists:
        profile.delete()
    if policy.exists:
        policy.delete()
    if action.exists:
        action.delete()


class VMEvent(object):
    """Class for generating  events on a VM in order to check it on Timelines.
    Args:
        vm: A VM object (Object)
        event: an event, Key in ACTIONS.(String)
    """
    ACTIONS = {
        'create': {
            'tl_event': ('VmDeployedEvent',
                         'USER_RUN_VM',
                         'USER_ADD_VM_FINISHED_SUCCESS',
                         ),
            'tl_category': 'Creation/Addition',
            'db_event_type': ('vm_create', 'USER_RUN_VM'),
            'emit_cmd': '_setup_vm'
        },
        'start': {
            'tl_event': ('VmPoweredOnEvent', 'USER_STARTED_VM', 'USER_RUN_VM'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_start',
            'emit_cmd': '_power_on'
        },
        'stop': {
            'tl_event': ('VmPoweredOffEvent', 'USER_STOP_VM', 'VM_DOWN'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_poweroff',
            'emit_cmd': '_power_off'
        },
        'suspend': {
            'tl_event': ('VmSuspendedEvent', 'USER_SUSPEND_VM', 'USER_SUSPEND_VM_OK'),
            'tl_category': 'Power Activity',
            'db_event_type': 'vm_suspend',
            'emit_cmd': '_suspend'
        },
        'rename': {
            'tl_event': ('VmRenamedEvent', 'USER_UPDATE_VM'),
            'tl_category': 'Alarm/Status Change/Errors',
            'db_event_type': 'VmRenamedEvent',
            'emit_cmd': '_rename_vm'
        },
        'delete': {
            'tl_event': ('VmRemovedEvent', 'DestroyVM_Task', 'USER_REMOVE_VM_FINISHED'),
            'tl_category': 'Deletion/Removal',
            'db_event_type': 'VmRenamedEvent',
            'emit_cmd': '_delete_vm'
        },
        'clone': {
            'tl_event': ('CloneVM_Task_Complete', 'CloneVM_Task'),
            'tl_category': 'Creation/Addition',
            'db_event_type': 'VmClonedEvent',
            'emit_cmd': '_clone_vm'
        },
        'migrate': {
            'tl_event': (
                'VmMigratedEvent',
                'RelocateVM_Task',
                'VM_MIGRATION_DONE',
                'VM_MIGRATION_FAILED_FROM_TO',  # allow for failure of migration
                'VM_MIGRATION_FAILED',
            ),
            'tl_category': 'Migration/Vmotion',
            'db_event_type': 'VmMigratedEvent',
            'emit_cmd': '_migrate_vm'
        },
        'policy': {
            'tl_event': ('vm_poweroff',),
            'tl_category': 'VM Operation',
            'emit_cmd': '_power_off'
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
            raise

    def _setup_vm(self):
        if not self.vm.exists_on_provider:
            logger.info('Will set up the VM %r ton the provider', self.vm.name)
            return self.vm.create_on_provider(find_in_cfme=True)
        else:
            logger.info('%r already exists on the provider.', self.vm.name)

    def _power_on(self):
        return self.vm.mgmt.start()

    def _power_off(self):
        return self.vm.mgmt.stop()

    def _restart_vm(self):
        return self._power_off() and self._power_on()

    def _suspend(self):
        return (self.vm.mgmt.suspend() and self.vm.mgmt.start())

    def _rename_vm(self):
        logger.info('%r will be renamed', self.vm.name)
        new_name = self.vm.name + '-renamed'
        rename_success = self.vm.mgmt.rename(self.vm.name + '-renamed')
        if not rename_success:
            raise Exception(
                'Renaming {} to {} on the provider failed'.format(
                    self.vm.name, new_name)
            )
        logger.info('%r new name is %r', self.vm.name, new_name)
        self.vm.name = new_name
        logger.info('%r will be rebooted', self.vm.name)
        self.vm.mgmt.restart()
        return self.vm.name

    def _delete_vm(self):
        logger.info('%r will be deleted.', self.vm.name)
        return self.vm.mgmt.delete()

    def _clone_vm(self):
        msg = '{name} will be cloned to {name}-clone.'.format(name=self.vm.name)
        logger.info(msg)
        clone_name = self.vm.name + '-clone'
        self.vm.clone_vm(vm_name=clone_name)
        wait_for(self.vm.provider.mgmt.does_vm_exist, [clone_name], timeout='6m',
                 message='Check clone exists failed')

    def _migrate_vm(self):
        logger.info('%r will be migrated.', self.vm.name)
        view = navigate_to(self.vm, "Details")
        vm_host = view.entities.summary('Relationships').get_text_of('Host')
        hosts = [vds.name for vds in self.vm.provider.hosts.all() if vds.name not in vm_host]
        if hosts:
            migrate_to = hosts[0]
        else:
            pytest.skip("There is only one host in the provider")
        return self.vm.migrate_vm(host=migrate_to)

    def _check_timelines(self, target, policy_events):
        """Verify that the event is present in the timeline

        Args:
            target: A entity where a Timeline is present (VM, host, cluster, Provider...)
            policy_events: switch between the management event timeline and the policy timeline.
        Returns:
             The length of the array containing the event found on the Timeline of the target.
        """

        def _get_timeline_events(target, policy_events):
            """Navigate to the timeline of the target and select the management timeline or the
            policy timeline. Returns an array of the found events.
            """

            timelines_view = navigate_to(target, 'Timelines')

            if isinstance(timelines_view, ServerDiagnosticsView):
                timelines_view = timelines_view.timelines
            timeline_filter = timelines_view.filter

            if policy_events:
                logger.info('Will search in Policy event timelines')
                timelines_view.filter.event_type.select_by_visible_text('Policy Events')
                timeline_filter.policy_event_category.select_by_visible_text(self.tl_category)
                timeline_filter.policy_event_status.fill('Both')
            else:
                if timelines_view.browser.product_version < "5.10":
                    timeline_filter.detailed_events.fill(True)
                for selected_option in timeline_filter.event_category.all_selected_options:
                    timeline_filter.event_category.select_by_visible_text(selected_option)
                timeline_filter.event_category.select_by_visible_text(self.tl_category)

            timeline_filter.time_position.select_by_visible_text('centered')
            timeline_filter.apply.click()
            logger.info('Searching for event type: %r in timeline category: %r', self.event,
                        self.tl_category)
            return timelines_view.chart.get_events(self.tl_category)

        events_list = _get_timeline_events(target, policy_events)
        logger.debug('events_list: %r', str(events_list))

        if not len(events_list):
            self.vm.provider.refresh_provider_relationships()
            logger.warning('Event list of %r is empty!', str(target))

        found_events = []

        for evt in events_list:
            try:
                if not policy_events:
                    # Special case for create event
                    if hasattr(evt, 'destination_vm') and evt.destination_vm in self.vm.name:
                        found_events.append(evt)
                        break
                    # Other events
                    elif evt.source_vm in self.vm.name and evt.event_type in self.tl_event:
                        found_events.append(evt)
                        break
                    elif (
                        self.event == 'create' and
                        BZ(1687493,
                           unblock=lambda provider: not provider.one_of(RHEVMProvider)).blocks and
                        self.vm.name in evt.message and evt.event_type in self.tl_event
                    ):
                        found_events.append(evt)
                        break
                else:
                    if evt.event_type in self.tl_event and evt.target in self.vm.name:
                        found_events.append(evt)
                        break
            except AttributeError as err:
                logger.warning('Issue with TimelinesEvent: %r .Faulty event: %r', str(err),
                               str(evt))
                continue

        logger.info('found events on %r :\n %s', target, '\n'.join([repr(e) for e in found_events]))

        return len(found_events)

    def catch_in_timelines(self, soft_assert, targets, policy_events=False):
        if targets:
            for target in targets:
                try:
                    wait_for(self._check_timelines,
                             [target, policy_events],
                             timeout='7m',
                             fail_condition=0)
                except TimedOutError:
                    soft_assert(False, '0 occurrence of {} found on the timeline of {}'.format(
                        self.event, target))
        else:
            raise ValueError('Targets must not be empty')


@pytest.mark.meta(automates=[1747132])
def test_infra_timeline_create_event(new_vm, soft_assert):
    """Test that the event create is visible on the management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550
        1747132

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'create'
    vm_event = VMEvent(new_vm, event)
    if BZ(1747132, forced_streams=["5.10"]).blocks:
        targets = (new_vm, new_vm.cluster, new_vm.provider)
    else:
        targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {evt}failed'.format(evt=event))
    vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_timeline_policy_event(new_vm, control_policy, soft_assert):
    """Test that the category Policy Event is properly working on the Timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider. For this purpose, there is need to create a policy
    profile, assign it to the VM and stopping it which triggers the policy.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """

    event = 'policy'
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    vm_event = VMEvent(new_vm, event)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {} did timeout'.format(event))
    vm_event.catch_in_timelines(soft_assert, targets, policy_events=True)


def test_infra_timeline_stop_event(new_vm, soft_assert):
    """Test that the event Stop is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'stop'
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    vm_event = VMEvent(new_vm, event)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {} failed'.format(event))
    vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_timeline_start_event(new_vm, soft_assert):
    """Test that the event start is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'start'
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    vm_event = VMEvent(new_vm, event)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {} failed'.format(event))
    vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_timeline_suspend_event(new_vm, soft_assert):
    """Test that the event suspend is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider. The VM needs to be set before as management engine.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'suspend'
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    vm_event = VMEvent(new_vm, event)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {} failed'.format(event))
    vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_timeline_diagnostic(new_vm, soft_assert, mark_vm_as_appliance):
    """Test that the event create is visible on the appliance timeline ( EVM/configuration/Server/
    diagnostic/Timelines.

    Metadata:
        test_flag: events, provision, timelines

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'create'
    targets = (new_vm.appliance.server,)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    vm_event = VMEvent(new_vm, event)
    vm_event.catch_in_timelines(soft_assert, targets)


@pytest.mark.meta(blockers=[BZ(1622952)])
@pytest.mark.provider([VMwareProvider], override=True)
def test_infra_timeline_clone_event(new_vm, soft_assert):
    """Test that the event clone is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1622952
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'clone'
    vm_event = VMEvent(new_vm, event)
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {evt} failed'.format(evt=event))
    vm_event.catch_in_timelines(soft_assert, targets)


def test_infra_timeline_migrate_event(new_vm, soft_assert):
    """Test that the event migrate is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'migrate'
    vm_event = VMEvent(new_vm, event)
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {evt} failed'.format(evt=event))
    vm_event.catch_in_timelines(soft_assert, targets)


@pytest.mark.provider([VMwareProvider], override=True, scope='function')
def test_infra_timeline_rename_event(new_vm, soft_assert):
    """Test that the event rename is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.
    Action "rename" does not exist on RHV, thats why it is excluded.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1670550

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'rename'
    vm_event = VMEvent(new_vm, event)
    targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {evt} failed'.format(evt=event))
    vm_event.catch_in_timelines(soft_assert, targets)


@pytest.mark.meta(automates=[1747132])
def test_infra_timeline_delete_event(new_vm, soft_assert):
    """Test that the event delete is visible on the  management event timeline of the Vm,
    Vm's cluster,  VM's host, VM's provider.

    Metadata:
        test_flag: events, provision, timelines

    Bugzilla:
        1550488
        1670550
        1747132

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'delete'
    vm_event = VMEvent(new_vm, event)
    if BZ(1747132, forced_streams=["5.10"]).blocks:
        targets = (new_vm, new_vm.cluster, new_vm.provider)
    else:
        targets = (new_vm, new_vm.cluster, new_vm.host, new_vm.provider)
    logger.info('Will generate event %r on machine %r', event, new_vm.name)
    wait_for(vm_event.emit, timeout='7m', message='Event {evt} failed'.format(evt=event))
    navigate_to(new_vm, 'ArchiveDetails')
    vm_event.catch_in_timelines(soft_assert, targets)
