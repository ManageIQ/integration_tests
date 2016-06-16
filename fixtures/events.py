# -*- coding: utf-8 -*-
"""Event testing framework.

Some very important tips:

* You should run with artifactor in order to get per-test HTML event reports.

Usage of ``register_event`` is explained in :py:func:`register_event`.

Uses :py:class:`utils.events.EventTool` through :py:class:`utils.appliance.IPAppliance`.

Available event types:

* ``assigned_company_tag``
* ``assigned_company_tag_parent_ems_cluster``
* ``assigned_company_tag_parent_host``
* ``assigned_company_tag_parent_resource_pool``
* ``assigned_company_tag_parent_storage``
* ``containerimage_compliance_check``
* ``containerimage_compliance_failed``
* ``containerimage_compliance_passed``
* ``containerimage_created``
* ``containerimage_scan_complete``
* ``cpu_usage_100``
* ``cpu_usage_50``
* ``cpu_usage_75``
* ``cpu_usage_90``
* ``disk_usage_100``
* ``disk_usage_50``
* ``disk_usage_75``
* ``disk_usage_90``
* ``ems_auth_changed``
* ``ems_auth_error``
* ``ems_auth_incomplete``
* ``ems_auth_invalid``
* ``ems_auth_unreachable``
* ``ems_auth_valid``
* ``ems_performance_gap_detected``
* ``evm_server_boot_disk_high_usage``
* ``evm_server_db_backup_low_space``
* ``evm_server_db_disk_high_usage``
* ``evm_server_home_disk_high_usage``
* ``evm_server_is_master``
* ``evm_server_memory_exceeded``
* ``evm_server_miq_tmp_disk_high_usage``
* ``evm_server_not_responding``
* ``evm_server_start``
* ``evm_server_stop``
* ``evm_server_system_disk_high_usage``
* ``evm_server_tmp_disk_high_usage``
* ``evm_server_var_disk_high_usage``
* ``evm_server_var_log_audit_disk_high_usage``
* ``evm_server_var_log_disk_high_usage``
* ``evm_worker_exit_file``
* ``evm_worker_killed``
* ``evm_worker_memory_exceeded``
* ``evm_worker_not_responding``
* ``evm_worker_start``
* ``evm_worker_stop``
* ``evm_worker_uptime_exceeded``
* ``host_add_to_cluster``
* ``host_auth_changed``
* ``host_auth_error``
* ``host_auth_incomplete``
* ``host_auth_invalid``
* ``host_auth_unreachable``
* ``host_auth_valid``
* ``host_compliance_check``
* ``host_compliance_failed``
* ``host_compliance_passed``
* ``host_connect``
* ``host_disconnect``
* ``host_perf_complete``
* ``host_provisioned``
* ``host_remove_from_cluster``
* ``host_scan_complete``
* ``mem_usage_100``
* ``mem_usage_50``
* ``mem_usage_75``
* ``mem_usage_90``
* ``request_assign_company_tag``
* ``request_host_disable_vmotion``
* ``request_host_enable_vmotion``
* ``request_host_enter_maintenance_mode``
* ``request_host_exit_maintenance_mode``
* ``request_host_reboot``
* ``request_host_reset``
* ``request_host_scan``
* ``request_host_shutdown``
* ``request_host_standby``
* ``request_host_start``
* ``request_host_stop``
* ``request_service_retire``
* ``request_service_start``
* ``request_service_stop``
* ``request_storage_scan``
* ``request_unassign_company_tag``
* ``request_vm_create_snapshot``
* ``request_vm_destroy``
* ``request_vm_pause``
* ``request_vm_poweroff``
* ``request_vm_reboot_guest``
* ``request_vm_reset``
* ``request_vm_retire``
* ``request_vm_scan``
* ``request_vm_shelve``
* ``request_vm_shelve_offload``
* ``request_vm_shutdown_guest``
* ``request_vm_standby_guest``
* ``request_vm_start``
* ``request_vm_suspend``
* ``request_vm_unregister``
* ``service_provisioned``
* ``service_retire_warn``
* ``service_retired``
* ``service_started``
* ``service_stopped``
* ``storage_scan_complete``
* ``unassigned_company_tag``
* ``unassigned_company_tag_parent_ems_cluster``
* ``unassigned_company_tag_parent_host``
* ``unassigned_company_tag_parent_resource_pool``
* ``unassigned_company_tag_parent_storage``
* ``vm_clone``
* ``vm_clone_start``
* ``vm_compliance_check``
* ``vm_compliance_failed``
* ``vm_compliance_passed``
* ``vm_create``
* ``vm_migrate``
* ``vm_pause``
* ``vm_perf_complete``
* ``vm_poweroff``
* ``vm_provisioned``
* ``vm_reboot_guest``
* ``vm_reconfigure``
* ``vm_remote_console_connected``
* ``vm_renamed_event``
* ``vm_reset``
* ``vm_resume``
* ``vm_retire_warn``
* ``vm_retired``
* ``vm_scan_abort``
* ``vm_scan_complete``
* ``vm_scan_start``
* ``vm_shelve``
* ``vm_shelve_offload``
* ``vm_shutdown_guest``
* ``vm_snapshot``
* ``vm_snapshot_complete``
* ``vm_standby_guest``
* ``vm_start``
* ``vm_suspend``
* ``vm_template``
* ``vm_unregister``

The types can be retrieved using the :py:class:`utils.events.EventTool` by calling
:py:meth:`utils.events.EventTool.all_event_types` on it.
"""
from datetime import datetime

import pytest

from fixtures.artifactor_plugin import art_client, get_test_idents
from fixtures.pytest_store import store
from utils.datafile import template_env
from utils.log import create_logger
from utils.wait import wait_for, TimedOutError

logger = create_logger('events')


class HTMLReport(object):
    def __init__(self, test_name, registered_events, all_events):
        self.registered_events = registered_events
        self.test_name = test_name
        self.all_events = all_events

    def generate(self):
        template = template_env.get_template('event_testing.html')
        return template.render(
            test_name=self.test_name,
            registered_events=self.registered_events,
            all_events=self.all_events)


class EventExpectation(object):
    """ Expectation for an event.

    This object embeds an expectation in order to be able to easily compare
    whether the two expectations are the same but just with different time.

    This is the actual object returned by the :py:func:`register_event` fixture.
    """

    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, target_type, target_id, event_type, time=None):
        self.target_type = target_type
        self.target_id = target_id
        self.event_type = event_type
        self.arrived = None
        # These two following attributes are set from the events that come
        self.message = None
        self.id = id
        self.real_target_id = None
        if time:
            self.time = time
        else:
            self.time = datetime.utcnow()

    def __eq__(self, other):
        try:
            return (
                self.target_type == other.target_type and self.target_id == other.target_id and
                self.event_type == other.event_type)
        except AttributeError:
            return False

    @property
    def colour(self):
        return "green" if self.arrived else "red"

    @property
    def time_friendly(self):
        return datetime.strftime(self.time, self.TIME_FORMAT)

    @property
    def success_friendly(self):
        return "success" if self.arrived else "failed"

    @property
    def time_difference(self):
        if self.arrived:
            td = self.arrived - self.time
            return int(round(td.total_seconds()))
        else:
            return "Did not come"

    @property
    def query_params(self):
        return {
            'target_type': self.target_type, 'target_id': self.target_id,
            'event_type': self.event_type, 'since': self.time}


class EventListener(object):

    def __init__(self, appliance=None):
        self.started = False
        self.expectations = []
        # last_id is used to "clear" the database
        # When database is "cleared" the id of the last event is placed here. That is then used
        # in queries to prevent events of this id and earlier to get in.
        self.last_id = None
        self.appliance = appliance or store.current_appliance

    def delete_database(self):
        try:
            last_record = self.appliance.events.query_miq_events()[-1]
            self.last_id = last_record['id']
        except IndexError:
            # No events yet, so do nothing
            pass

    def get_all_received_events(self):
        return self.appliance.events.query_miq_events(from_id=self.last_id)

    def check_all_expectations(self):
        """ Check whether all triggered events have been captured.

        Sets a flag for each event.

        Returns:
            Boolean whether all events have already been captured.

        """
        until = datetime.utcnow()
        seen_ids = set()
        for expectation in self.expectations:
            try:
                arrived_events = self.appliance.events.query_miq_events(
                    until=until, from_id=self.last_id, **expectation.query_params)
            except ValueError:
                # An object name - not present in the database yet - assuming the event has not come
                # .... yet
                continue
            for event in arrived_events:
                if event['id'] in seen_ids:
                    # Already processed
                    continue
                seen_ids.add(event['id'])
                expectation.arrived = event['timestamp']
                expectation.message = event['message']
                expectation.id = event['id']
                expectation.real_target_id = event['target_id']
                logger.info(
                    'Detected event {}/{} from {}/{} ({}): {}'.format(
                        expectation.id,
                        expectation.event_type,
                        expectation.target_id,
                        expectation.real_target_id,
                        expectation.target_type,
                        expectation.message))
        return all(exp.arrived is not None for exp in self.expectations)

    @property
    def expectations_count(self):
        return len(self.expectations)

    def add_expectation(self, *args):
        # Time added automatically if not given
        self.expectations.append(EventExpectation(*args))

    def __call__(self, target_type, target_id, event_types):
        if not self.started:
            # Ignore
            return
        if not isinstance(event_types, (list, tuple, set)):
            event_types = [event_types]
        for event_type in event_types:
            logger.info("Event %s registration for %s/%d", event_type, target_type, target_id)
            self.add_expectation(target_type, target_id, event_type)

    def start(self):
        self.started = True


def pytest_addoption(parser):
    parser.addoption('--event-testing',
                     action='store_true',
                     dest='event_testing_enabled',
                     default=False,
                     help='Enable testing of the events. (default: %default)')


@pytest.mark.trylast
def pytest_configure(config):
    """ Event testing setup.

    Sets up and registers the EventListener plugin for py.test.
    If the testing is enabled, listener is started.
    """
    plugin = EventListener()
    registration = config.pluginmanager.register(plugin, "event_testing")
    assert registration
    if config.getoption("event_testing_enabled"):
        plugin.start()


@pytest.fixture(scope="function")
def register_event(
        uses_event_listener, request, soft_assert):
    """register_event(target_type, target_id, event_types)
    Event registration fixture.

    This fixture is used to notify the testing system that some event
    should have occured during execution of the test case using it.
    It does not register anything by itself.

    Args:
        target_type: Target type, in form of classname (VmOrTemplate, Host, Service, ...)
        target_id: Database id (integer) of the object, but you can use a string in form of the
            object's name since the :py:class:`utils.events.EventTool` can retrieve the id by itself
        event_types: Names of the event(s). Can be either a string or a list of strings

    Returns: :py:class:`EventExpectation`

    Usage:

        def test_something(foo, bar, register_event):
            register_event("VmOrTemplate", 123, 'vm_start')
            # or
            register_event("VmOrTemplate", 123, ['request_vm_start', 'vm_start'])
            # do_some_stuff_that_triggers()
    """
    # We pull out the plugin directly.
    self = request.config.pluginmanager.getplugin("event_testing")  # Workaround for bind

    if self.started:
        logger.info("Clearing the database before testing ...")
        self.delete_database()
        self.expectations = []

    return self  # Run the test and provide the plugin as a fixture


@pytest.mark.hookwrapper
def pytest_runtest_call(item):
    """If we use register_event, then collect the events and fail the test if not all came.

    After the test function finishes, it checks the listener whether it has caught the events.
    It uses `soft_assert` fixture.
    Before and after each test run using `register_event` fixture, database is cleared.
    """
    if "register_event" in item.funcargs:
        register_event = item.funcargs["register_event"]
        store.current_appliance.wait_for_ssh()
        register_event.delete_database()
    else:
        register_event = None
    try:
        yield
    finally:
        if register_event is None:
            return

        node_id = item._nodeid

        # Event testing is enabled.
        try:
            logger.info('Checking the events to come.')
            wait_for(register_event.check_all_expectations,
                     delay=5,
                     num_sec=75,
                     handle_exception=True)
        except TimedOutError:
            logger.warning('Some of the events seem to not have come!')
        else:
            logger.info('Seems like all events have arrived!')

        name, location = get_test_idents(item)

        art_client.fire_hook(
            'filedump',
            test_name=name,
            test_location=location,
            description="Event testing report",
            contents=HTMLReport(
                node_id, register_event.expectations, register_event.get_all_received_events()
            ).generate(),
            file_type="html",
            display_glyph="align-justify",
            group_id="misc-artifacts",
        )
        logger.info("Clearing the database after testing ...")
        register_event.delete_database()
        soft_assert = item.funcargs["soft_assert"]
        for expectation in register_event.expectations:
            soft_assert(
                expectation.arrived,
                "Event {} for {} {} did not come!".format(
                    expectation.event_type, expectation.target_type, expectation.target_id))
        register_event.expectations = []
