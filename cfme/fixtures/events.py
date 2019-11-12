"""Event testing fixture.

The idea of this fixture is to pass some "expected" events to
:py:class:`utils.events.EventListener` and check whether all expected events are received
at the test end.

register_event fixture accepts attributes for one expected event

simple example:

.. code-block:: python

    register_event(target_type='VmOrTemplate', target_name=vm_crud.name, event_type='vm_create')

more complex example:

.. code-block:: python

    def add_cmp(_, y):
        data = yaml.safe_load(y)
        return data['resourceId'].endswith(nsg_name) and data['status']['value'] == 'Accepted' and \
            data['subStatus']['value'] == 'Created'

    fd_add_attr = {'full_data': 'will be ignored',
                   'cmp_func': add_cmp}

    # add network security group event
    register_event(fd_add_attr, source='AZURE',
                   event_type='networkSecurityGroups_write_EndRequest')

    def rm_cmp(_, y):
        data = yaml.safe_load(y)
        return data['resourceId'].endswith(nsg_name) and data['status']['value'] == 'Succeeded' \
            and len(data['subStatus']['value']) == 0

    fd_rm_attr = {'full_data': 'will be ignored',
                  'cmp_func': rm_cmp}

    # remove network security group event
    register_event(fd_rm_attr, source=provider.type.upper(),
                   event_type='networkSecurityGroups_delete_EndRequest')

Expected events are defined by set of event attributes which should match to the same event
attributes in event_streams db table except one fake attribute - target_name which is resolved into
certain object's id.

Default match algorithm is ==. Event also accepts match function in order to change default
match type.
"""
import logging

import pytest

from cfme.utils.log import setup_logger
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


# xxx better logger name
logger, _ = setup_logger(logging.getLogger('events'))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    try:
        yield
    finally:
        if "register_event" in item.fixturenames:
            event_listener = item.funcargs["register_event"]
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


@pytest.fixture(scope="function")
def register_event(request, uses_event_listener, soft_assert, appliance):
    """register_event(list of event attributes)
    Event registration fixture.

    This fixture is used to notify the testing system that some event
    should have occurred during execution of the test case using it.
    It does not register anything by itself.

    Args:
        event attribute 1
        ...
        event attribute N

    Returns: None

    Usage:

        def test_something(foo, bar, register_event, appliance):
            register_event(target_type = 'VmOrTemplate', target_name = vm.name,
                event_type = 'vm_create')
    """
    event_listener = appliance.event_listener()
    event_listener.reset_events()
    event_listener.start()
    yield event_listener

    event_listener.stop()
    event_listener.reset_events()
