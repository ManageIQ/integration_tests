# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from wrapanapi.exceptions import NotFoundError

from cfme import test_requirements
from cfme.base.ui import ServerDiagnosticsView
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.control.explorer.policies import VMControlPolicy
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(2),
    # Only onr prov out of the 2 is taken, if not supplying --use-provider=complete
    pytest.mark.provider([AzureProvider, EC2Provider]),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.timelines,
    test_requirements.events,
]


@pytest.fixture(scope='function')
def new_instance(appliance, provider):
    inst = appliance.collections.cloud_instances.instantiate(
        random_vm_name('cloud-timeline', max_length=20), provider)
    logger.debug('Fixture new_instance set up! Name: %r Provider: %r',
                 inst.name, inst.provider.name)
    inst.create_on_provider(allow_skip="default", find_in_cfme=True)
    yield inst
    logger.debug('Fixture new_instance teardown! Name: %r Provider: %r',
                 inst.name, inst.provider.name)
    try:
        inst.mgmt.cleanup()
    except NotFoundError:
        pass


@pytest.fixture(scope="function")
def mark_vm_as_appliance(new_instance, appliance):
    # set diagnostics vm
    relations_view = navigate_to(new_instance, 'EditManagementEngineRelationship', wait_for_view=0)
    relations_view.form.server.select_by_visible_text(
        "{name} ({sid})".format(
            name=appliance.server.name,
            sid=appliance.server.sid
        )
    )
    relations_view.form.save_button.click()


@pytest.fixture(scope='function')
def control_policy(appliance, new_instance):
    action = appliance.collections.actions.create(fauxfactory.gen_alpha(), "Tag",
            dict(tag=("My Company Tags", "Environment", "Development")))
    policy = appliance.collections.policies.create(VMControlPolicy, fauxfactory.gen_alpha())
    policy.assign_events("VM Power Off")
    policy.assign_actions_to_event("VM Power Off", action)

    profile = appliance.collections.policy_profiles.create(fauxfactory.gen_alpha(),
                                                           policies=[policy])

    yield new_instance.assign_policy_profiles(profile.description)
    for obj in [profile, policy, action]:
        if obj.exists:
            obj.delete()


@pytest.fixture(scope='function')
def azone(new_instance, appliance):
    zone_id = new_instance.get_vm_via_rest().availability_zone_id
    rest_zones = new_instance.appliance.rest_api.collections.availability_zones
    zone_name = next(zone.name for zone in rest_zones if zone.id == zone_id)
    inst_zone = appliance.collections.cloud_av_zones.instantiate(name=zone_name,
                                                                 provider=new_instance.provider)
    return inst_zone


class InstEvent(object):
    ACTIONS = {
        'create': {
            'tl_event': ('AWS_EC2_Instance_CREATE', 'virtualMachines_write_EndRequest'),
            'tl_category': 'Creation/Addition',
            'db_event_type': ('AWS_EC2_Instance_CREATE', 'virtualMachines_write_EndRequest'),
            'emit_cmd': '_create_vm'
        },
        'start': {
            'tl_event': (
                'AWS_API_CALL_StartInstances', 'AWS_EC2_Instance_running',
                'virtualMachines_start_EndRequest'
            ),
            'tl_category': 'Power Activity',
            'db_event_type': (
                'AWS_EC2_Instance_running', 'virtualMachines_start_EndRequest'),
            'emit_cmd': '_power_on'
        },
        'stop': {
            'tl_event': (
                'AWS_API_CALL_StopInstances', 'AWS_EC2_Instance_stopped',
                'virtualMachines_deallocate_EndRequest'
            ),
            'tl_category': 'Power Activity',
            'db_event_type': ('AWS_EC2_Instance_stopped', 'virtualMachines_deallocate_EndRequest'),
            'emit_cmd': '_power_off'
        },
        'rename': {
            'tl_event': 'AWS_EC2_Instance_CREATE',
            'tl_category': 'Creation/Addition',
            'db_event_type': 'AWS_EC2_Instance_CREATE',
            'emit_cmd': '_rename_vm'
        },
        'delete': {
            'tl_event': (
                'virtualMachines_delete_EndRequest',
                'AWS_EC2_Instance_DELETE',
                'AWS_API_CALL_TerminateInstances',
            ),
            'tl_category': 'Deletion/Removal',
            'db_event_type': (
                'virtualMachines_delete_EndRequest',
                'AWS_API_CALL_TerminateInstances'
            ),
            'emit_cmd': '_delete_vm'
        },
        'policy': {
            'tl_event': ('vm_poweroff',),
            'tl_category': 'VM Operation',
            'emit_cmd': '_power_off'
        },
    }

    def __init__(self, inst, event):
        self.inst = inst
        self.event = event
        self.__dict__.update(self.ACTIONS[self.event])

    def emit(self):
        try:
            emit_action = getattr(self, self.emit_cmd)
            emit_action()
        except AttributeError:
            raise AttributeError('{} is not a valid key in ACTION. self: {}'.format(self.event,
                                                                                    self.__dict__))

    def _create_vm(self):
        if not self.inst.exists_on_provider:
            self.inst.create_on_provider(allow_skip="default", find_in_cfme=True)
        else:
            logger.info('%r already exists on provider', self.inst.name)

    def _power_on(self):
        return self.inst.mgmt.start()

    def _power_off(self):
        return self.inst.mgmt.stop()

    def _power_off_power_on(self):
        self.inst.mgmt.stop()
        return self.inst.mgmt.start()

    def _restart(self):
        return self.inst.mgmt.restart()

    def _rename_vm(self):
        logger.info('%r will be renamed', self.inst.name)
        new_name = "{}-renamed".format(self.inst.name)
        self.inst.mgmt.rename(new_name)
        self.inst.name = new_name
        self.inst.mgmt.restart()
        self.inst.provider.refresh_provider_relationships()
        self.inst.wait_to_appear()
        return self.inst.name

    def _delete_vm(self):
        try:
            logger.info("attempting to delete vm %s", self.inst.name)
            self.inst.mgmt.cleanup()
        except NotFoundError:
            logger.info("can't delete vm %r, does not exist", self.inst.name)
            pass

    def _check_timelines(self, target, policy_events):
        """Verify that the event is present in the timeline

        Args:
            target: A entity where a Timeline is present (Instance, Availability zone, Provider...)
            policy_events: switch between the management event timeline and the policy timeline.
        Returns:
             The length of the array containing the event found on the Timeline of the target.
        """

        def _get_timeline_events(target, policy_events):
            """Navigate to the timeline of the target and select the management timeline or the
            policy timeline. Returns an array of the found events.
            """

            timelines_view = navigate_to(target, 'Timelines', wait_for_view=20, force=True)

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

        if not events_list:
            self.inst.provider.refresh_provider_relationships()
            logger.warn('Event list of %r is empty!', target)

        found_events = []

        for evt in events_list:
            try:
                if not policy_events:
                    if evt.source_instance in self.inst.name and evt.event_type in self.tl_event:
                        found_events.append(evt)
                        break
                else:
                    if evt.event_type in self.tl_event and evt.target in self.inst.name:
                        found_events.append(evt)
                        break
            except AttributeError as err:
                logger.warn('Issue with TimelinesEvent: %r .Faulty event: %r', str(err), str(evt))
                continue

        logger.info('found events on %r: %s', target, "\n".join([repr(e) for e in found_events]))

        return len(found_events)

    def catch_in_timelines(self, soft_assert, targets, policy_events=False):
        for target in targets:
            try:
                wait_for(self._check_timelines,
                         [target, policy_events],
                         timeout='15m',
                         fail_condition=0)
            except TimedOutError:
                soft_assert(False, '0 occurrence of {evt} found on the timeline of {tgt}'.format(
                    evt=self.event, tgt=target))


def test_cloud_timeline_create_event(new_instance, soft_assert, azone):
    """
    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider, azone)
    event = 'create'
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='9m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets)


def test_cloud_timeline_policy_event(new_instance, control_policy, soft_assert):
    """
    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'policy'
    # accordions on azone and provider's page are not displayed in 5.10
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider)
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='9m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets, policy_events=True)


def test_cloud_timeline_stop_event(new_instance, soft_assert, azone):
    """
    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    # accordions on azone and provider's page are not displayed in 5.10
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider, azone)
    event = 'stop'
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='7m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets)


def test_cloud_timeline_start_event(new_instance, soft_assert, azone):
    """
    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    # accordions on azone and provider's page are not displayed in 5.10
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider, azone)
    event = 'start'
    inst_event = InstEvent(new_instance, 'start')
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='7m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets)


def test_cloud_timeline_diagnostic(new_instance, mark_vm_as_appliance, soft_assert):
    """Check Configuration/diagnostic/timelines.

    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'create'
    targets = (new_instance.appliance.server,)
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    inst_event.catch_in_timelines(soft_assert, targets)


@pytest.mark.provider([EC2Provider], override=True, scope='function')
def test_cloud_timeline_rename_event(new_instance, soft_assert, azone):
    """
    Metadata:
        test_flag: timelines, events

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'rename'
    # accordions on azone and provider's page are not displayed in 5.10
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider, azone)
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='12m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets)


@pytest.mark.meta(automates=[1730819], blockers=[BZ(1730819, forced_streams=["5.11"])])
def test_cloud_timeline_delete_event(new_instance, soft_assert, azone):
    """
    Metadata:
        test_flag: timelines, events

    Bugzilla:
        1730819

    Polarion:
        assignee: jdupuy
        initialEstimate: 1/4h
        casecomponent: Events
    """
    event = 'delete'
    # accordions on azone and provider's page are not displayed in 5.10
    if BZ(1670550).blocks:
        targets = (new_instance, )
    else:
        targets = (new_instance, new_instance.provider, azone)
    inst_event = InstEvent(new_instance, event)
    logger.info('Will generate event %r on machine %r', event, new_instance.name)
    wait_for(inst_event.emit, timeout='9m', message='Event {} did timeout'.format(event))
    inst_event.catch_in_timelines(soft_assert, targets)
