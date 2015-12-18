# -*- coding: utf-8 -*-
"""Event testing framework.

Some very important tips:

* You MUST have your firewall turned off if you use random ports (as it is done in tests). If you
  use a specific fixed port, make sure it is reachable from outside.
* If you develop tests that use event testing, create a config in env.yaml:

  .. code-block:: yaml

    event_testing:
        port: 12345

  Then in multiple runs, the port stays the same so it works. Failure to do this will bite you. If
  you forgot to do that, you can change the hostname and ip of event listener at Automate's
  ``Datastore/EventTesting/QE/Automation/APIMethods/relay_events``. You can run the listener
  standalone using ``python scripts/listener.py 0.0.0.0 <port>`` and use it for development.
  It will eat all events that come to it and you will be able to see them at
  ``localhost:port/events``, although just in JSON (rendering of HTML is done in cfme_tests). You
  can issue a ``DELETE /events`` on the listener (eg. using ``curl``) in order to flush the event
  database.

* You should run with artifactor in order to get per-test HTML event reports.

Usage of ``register_event`` is explained in :py:func:`register_event`.
"""
import requests
import signal
import subprocess
import time
from datetime import datetime

import pytest

from fixtures.artifactor_plugin import art_client, get_test_idents
from fixtures.terminalreporter import reporter
from utils import lazycache
from utils import providers
from utils.conf import env
from utils.db import cfmedb
from utils.datafile import template_env
from utils.events import setup_for_event_testing
from utils.log import create_logger
from utils.net import my_ip_address, random_port
from utils.path import scripts_path
from utils.ssh import SSHClient
from utils.wait import wait_for, TimedOutError

logger = create_logger('events')


def get_current_time_GMT():
    """ Because SQLite loves GMT.

    Returns:
        datetime() with current GMT time
    """
    return datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "%Y-%m-%d %H:%M:%S")


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

    def __init__(self, sys_type, obj_type, obj, event, time=None):
        self.sys_type = sys_type
        self.obj_type = obj_type
        self.obj = obj
        self.event = event
        self.arrived = None
        if time:
            self.time = time
        else:
            self.time = get_current_time_GMT()

    def __eq__(self, other):
        try:
            assert self.sys_type == other.sys_type
            assert self.obj_type == other.obj_type
            assert self.obj == other.obj
            assert self.event == other.event
            return True
        except (AssertionError, AttributeError):
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


class EventListener(object):

    TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

    def __init__(self, verbose=False):
        listener_filename = scripts_path.join('listener.py').strpath
        self.listener_script = "{} 0.0.0.0 {}".format(listener_filename, self.listener_port)
        if not verbose:
            self.listener_script += ' --quiet'
        self.expectations = []
        self.listener = None

    @lazycache
    def listener_port(self):
        return env.get("event_listener", {}).get("port", None) or random_port()

    def listener_host(self):
        return "http://%s" % my_ip_address()

    def _get(self, route):
        """ Query event listener
        """
        assert not self.finished, "Listener dead!"
        listener_url = "%s:%d" % (self.listener_host(), self.listener_port)
        logger.info("checking api: %s%s" % (listener_url, route))
        r = requests.get(listener_url + route)
        r.raise_for_status()
        response = r.json()
        logger.debug("Response: %s" % response)
        return response

    def _delete_database(self):
        """ Sends a DELETE /events request for listener.

        Listener reacts to this kind of request by truncating contents of the events table.

        Returns:
            Boolean signalizing success.
        """
        assert not self.finished, "Listener dead!"
        listener_url = "%s:%d" % (self.listener_host(), self.listener_port)
        r = requests.delete(listener_url + "/events")
        r.raise_for_status()
        return r.json().get("result") == "success"

    def mgmt_sys_type(self, sys_type, obj_type):
        """ Map management system type from cfme_data.yaml to match event string
            and also add possibility of host based test.
        """
        # TODO: obj_type ('ems' or 'vm') is the same for all tests in class
        #       there must be a better way than to pass this around
        ems_map = {"rhevm": "EmsRedhat",
                   "virtualcenter": "EmsVmware"}
        vm_map = {"rhevm": "VmRedhat",
                  "virtualcenter": "VmVmware"}
        if obj_type in {"ems"}:
            return ems_map.get(sys_type)
        elif obj_type in {"vm"}:
            return vm_map.get(sys_type)
        elif obj_type in {"host"}:
            return obj_type

    def check_db(self, sys_type, obj_type, obj, event, after=None, before=None):
        """ Utility to check listener database for event

        Args:
            after: Return only events that happened AFTER this time
            before: Return only events that happened BEFORE this time

        Note:
            Both can be combined. If None, then the filter won't be applied.
        """
        max_attempts = 10
        sleep_interval = 2
        req = "/events/%s/%s?event=%s" % (self.mgmt_sys_type(sys_type, obj_type), obj, event)
        # Timespan limits
        if after:
            req += "&from_time=%s" % datetime.strftime(after, self.TIME_FORMAT)
        if before:
            req += "&to_time=%s" % datetime.strftime(before, self.TIME_FORMAT)

        for attempt in range(1, max_attempts + 1):
            data = self._get(req)
            try:
                assert len(data) > 0
            except AssertionError as e:
                if attempt < max_attempts:
                    logger.debug("Waiting for DB (%s/%s): %s" % (attempt, max_attempts, e))
                    time.sleep(sleep_interval)
                    pass
                # Enough sleeping, something went wrong
                else:
                    logger.exception("Check DB failed. Max attempts: '%s'." % (max_attempts))
                    return False
            else:
                # No exceptions raised
                logger.info("DB row found for '%s'" % req)
                return datetime.strptime(data[0]["event_time"], "%Y-%m-%d %H:%M:%S")
        return False

    def get_all_received_events(self):
        return self._get("/events")

    def check_all_expectations(self):
        """ Check whether all triggered events have been captured.

        Sets a flag for each event.

        Simplified to check just against the time of registration
        and the begin of this check.

        Returns:
            Boolean whether all events have already been captured.

        """
        check_started = get_current_time_GMT()
        for expectation in self.expectations:
            # Get the events with the same parameters, just with different time
            the_same = [item
                        for item
                        in self.expectations
                        if item == expectation and item is not expectation
                        ]
            # Split them into preceeding and following events
            preceeding_events = [event
                                 for event
                                 in the_same
                                 if event.time <= expectation.time and event is not expectation
                                 ]
            # Get immediate predecessor's of follower's time of this event
            preceeding_event = preceeding_events[-1].time if preceeding_events else expectation.time
            # following_event = following_events[0].time if following_events else check_started
            # Shorten the params
            params = [expectation.sys_type,
                      expectation.obj_type,
                      expectation.obj,
                      expectation.event]
            came = self.check_db(*params, after=preceeding_event, before=check_started)
            if came:
                expectation.arrived = came
        return all([exp.arrived is not None for exp in self.expectations])

    @property
    def expectations_count(self):
        return len(self.expectations)

    def add_expectation(self, sys_type, obj_type, obj, event):
        expectation = EventExpectation(sys_type, obj_type, obj, event)  # Time added automatically
        self.expectations.append(expectation)

    def __call__(self, sys_type, obj_type, obj, events):
        if not isinstance(events, list):
            events = [events]
        for event in events:
            logger.info("Event registration: %s" % str(locals()))
            self.add_expectation(sys_type, obj_type, obj, event)

    @pytest.fixture(scope="session")
    def listener_info(self):
        """ Listener fixture

        This fixture provides listener's address and port.
        It is used in setup test cases located at:
        ``/tests/test_setup_event_testing.py``
        """
        return type(
            "Listener",
            (object,),
            {
                "host": self.listener_host(),
                "port": self.listener_port
            }
        )

    @property
    def finished(self):
        if not self.listener:
            return True
        return self.listener.poll() is not None

    def start(self):
        assert not self.listener, "Listener can't be running in order to start it!"
        logger.info("Starting listener %s" % self.listener_script)
        logger.info("In order to run the event testing, port %d must be enabled." %
            self.listener_port)
        logger.info("sudo firewall-cmd --add-port %d/tcp --permanent" % self.listener_port)
        self.listener = subprocess.Popen(self.listener_script,
                                         shell=True)
        logger.info("Listener pid %d" % self.listener.pid)
        time.sleep(3)
        assert not self.finished, "Listener has died. Something must be blocking selected port"
        logger.info("Listener alive")

    def stop(self):
        assert self.listener, "Listener must be running in order to stop it!"
        logger.info("Killing listener %d" % (self.listener.pid))
        self.listener.send_signal(signal.SIGINT)
        self.listener.wait()
        self.listener = None

    def pytest_unconfigure(self, config):
        """ Collect and clean up the testing.

        If the event testing is active, collects results, stops the listener
        and generates the report.
        """
        if config.getoption("event_testing_enabled"):
            # Collect results
            try:
                # Report to the terminal
                termreporter = reporter(config)
                termreporter.write_sep('-', 'Stopping event listener')
            finally:
                self.stop()


def pytest_addoption(parser):
    parser.addoption('--event-testing',
                     action='store_true',
                     dest='event_testing_enabled',
                     default=False,
                     help='Enable testing of the events. (default: %default)')
    parser.addoption('--event-testing-result',
                     action='store',
                     dest='event_testing_result',
                     default="log/events.html",
                     help='Filename of result report. (default: %default)')
    parser.addoption('--event-testing-verbose-listener',
                     action='store_true',
                     dest='event_testing_verbose_listener',
                     default=False,
                     help='Enabled access logging from the event listener')


def pytest_configure(config):
    """ Event testing setup.

    Sets up and registers the EventListener plugin for py.test.
    If the testing is enabled, listener is started.
    """
    plugin = EventListener(config.getoption("event_testing_verbose_listener"))
    registration = config.pluginmanager.register(plugin, "event_testing")
    assert registration
    if config.getoption("event_testing_enabled"):
        plugin.start()


@pytest.fixture(scope="module")
def configure_appliance_for_event_testing(request, listener_info):
    """ This fixture ensures that the appliance is configured for event testing.
    """
    event_testing = request.config.pluginmanager.getplugin("event_testing")
    # If we did not enable the event testing, do not setup
    if event_testing.listener is None:
        return
    return setup_for_event_testing(
        SSHClient(), cfmedb(), listener_info, providers.list_infra_providers()
    )


@pytest.fixture(scope="function")
def register_event(
        uses_event_listener, configure_appliance_for_event_testing, request, soft_assert):
    """register_event(sys_type, obj_type, obj, event)
    Event registration fixture (ALWAYS PLACE BEFORE PAGE NAVIGATION FIXTURE!)

    This fixture is used to notify the testing system that some event
    should have occured during execution of the test case using it.
    It does not register anything by itself.

    Args:
        sys_type: Management system type to expect
        obj_type: Management system related object type to expect
        obj: Expected identifier for related object
        event: Event name or list of event names to expect

    Returns: :py:class:`EventExpectation`

    Usage:

        def test_something(foo, bar, register_event):
            register_event("systype", "objtype", "obj", "event")
            # or
            register_event("systype", "objtype", "obj", ["event1", "event2"])
            # do_some_stuff_that_triggers()

    For host_events, use `None` for sys_type.

    It also registers the time when the registration was done so we can filter
    out the same events, but coming in other times (like vm on/off/on/off will
    generate 3 unique events, but twice, distinguishable only by time).
    It can also partially prevent scumbag 'Jimmy' ruining the test if he does
    something in the hypervisor that the listener registers.

    """
    # We pull out the plugin directly.
    self = request.config.pluginmanager.getplugin("event_testing")  # Workaround for bind

    if self.listener is not None:
        logger.info("Clearing the database before testing ...")
        self._delete_database()
        self.expectations = []

    return self  # Run the test and provide the plugin as a fixture


@pytest.mark.hookwrapper
def pytest_runtest_call(item):
    """If we use register_event, then collect the events and fail the test if not all came.

    After the test function finishes, it checks the listener whether it has caught the events.
    It uses `soft_assert` fixture.
    Before and after each test run using `register_event` fixture, database is cleared.
    """
    try:
        yield
    finally:
        if "register_event" not in item.funcargs:
            return

        node_id = item._nodeid
        register_event = item.funcargs["register_event"]
        # If the event testing is disabled, skip the collection and failing
        if register_event.listener is None:
            return

        # Event testing is enabled.
        try:
            wait_for(register_event.check_all_expectations,
                     delay=5,
                     num_sec=75,
                     handle_exception=True)
        except TimedOutError:
            pass

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
        register_event._delete_database()
        soft_assert = item.funcargs["soft_assert"]
        for expectation in register_event.expectations:
            soft_assert(expectation.arrived, "Event {} did not come!".format(expectation.event))
        register_event.expectations = []
