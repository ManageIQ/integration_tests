# -*- coding: utf-8 -*-
"""Event testing fixture.

The idea of this fixture is to pass some "expected" events to
:py:class:`utils.events.EventListener` and check whether all expected events are received
at the test end.

register_event fixture accepts one or several expected events.

simple example:
    from utils.events import EventBuilder
    event = EventBuilder().new_event(target_type = 'VmOrTemplate',
                                     target_name = vm_crud.name,
                                     event_type = 'vm_create')
    register_event(event)
more complex example:

    from utils.events import EventBuilder
    builder = EventBuilder()
    fd_regexp = '^\s*resourceId:.*?{nsg}.*?^\s*status:.*?^\s*value:\s*{stat}.*?^' \
                '\s*subStatus:.*?^\s*value:\s*{sstat}'
    add_cmp = lambda _, y: bool(re.search(fd_regexp.format(nsg=nsg_name, stat='Accepted',
                                                           sstat='Created'), y, re.M | re.U | re.S))
    fd_add_attr = {'full_data': 'will be ignored',
                       'cmp_func': add_cmp}
    add_event = builder.new_event(fd_add_attr, source='AZURE',
                                      event_type='networkSecurityGroups_write_EndRequest')
    register_event(add_event)

Expected events are defined by set of event attributes which should match to the same event
attributes in event_streams db table except one fake attribute - target_name which is resolved into
certain object's id.

Default match algorithm is ==. Event also accepts match function in order to change default
match type.
"""
import logging
import pytest

from utils.appliance import get_or_create_current_appliance
from utils.events import EventListener
from utils.log import setup_logger
from utils.wait import wait_for, TimedOutError


# xxx better logger name
logger = setup_logger(logging.getLogger('events'))


class EventListenerWrapper(object):

    def __init__(self):
        self._cur_appliance = get_or_create_current_appliance()
        self._instances = []

    def _register_instance(self, inst):
        self._instances.append(inst)

    def _unregister_instance(self):
        self._instances.pop()

    def new_instance(self):
        inst = EventListener(self._cur_appliance)
        self._register_instance(inst)
        return inst

    @property
    def current_instance(self):
        try:
            return self._instances[-1]
        except IndexError:
            return None

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        if "register_event" in item.funcargnames:
            # store.current_appliance.wait_for_ssh()
            event_listener = self.new_instance()
            event_listener.reset_events()
            event_listener.start()
            event_listener.set_last_record()

        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        try:
            yield
        finally:
            if "register_event" in item.funcargnames:
                event_listener = self.current_instance
                soft_assert = item.funcargs["soft_assert"]

                try:
                    logger.info('Checking the events to come.')
                    wait_for(event_listener.check_expected_events,
                             delay=5,
                             num_sec=180,
                             handle_exception=True)
                except TimedOutError:
                    logger.info('checking collected events')
                    for event in event_listener.got_events:
                        soft_assert(len(event['matched_events']),
                                    "Event {} did not come!".format(event['event']))
                else:
                    logger.info('Seems like all events have arrived!')

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        if "register_event" in item.funcargnames:
            event_listener = self.current_instance
            event_listener.stop()
            event_listener.reset_events()
            self._unregister_instance()
        yield


def pytest_configure(config):
    plugin = EventListenerWrapper()
    registration = config.pluginmanager.register(plugin, "event_testing")
    assert registration


@pytest.fixture(scope="function")
def register_event(request, uses_event_listener, soft_assert):
    """register_event(list of events)
    Event registration fixture.

    This fixture is used to notify the testing system that some event
    should have occurred during execution of the test case using it.
    It does not register anything by itself.

    Args:
        event 1
        ...
        event N

    Returns: None

    Usage:

        def test_something(foo, bar, register_event):
            event = EventBuilder().new_event(target_type = 'VmOrTemplate',
                                             target_name = vm_crud.name,
                                             event_type = 'vm_create')
            register_event(event)

    """
    # We pull out the plugin directly.
    self = request.config.pluginmanager.getplugin("event_testing")

    return self.current_instance  # Run the test and provide the plugin as a fixture
