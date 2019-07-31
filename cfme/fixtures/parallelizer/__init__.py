"""Parallel testing, supporting arbitrary collection ordering

The Workflow
------------

- Master py.test process starts up, inspects config to decide how many slave to start, if at all
- py.test config.option.appliances and the related --appliance cmdline flag are used to count
  the number of needed slaves
- Slaves are started
- Master runs collection, blocks until slaves report their collections
- Slaves each run collection and submit them to the master, then block inside their runtest loop,
  waiting for tests to run
- Master diffs slave collections against its own; the test ids are verified to match
  across all nodes
- Master enters main runtest loop, uses a generator to build lists of test groups which are then
  sent to slaves, one group at a time
- For each phase of each test, the slave serializes test reports, which are then unserialized on
  the master and handed to the normal pytest reporting hooks, which is able to deal with test
  reports arriving out of order
- Before running the last test in a group, the slave will request more tests from the master

  - If more tests are received, they are run
  - If no tests are received, the slave will shut down after running its final test

- After all slaves are shut down, the master will do its end-of-session reporting as usual, and
  shut down

"""
import difflib
import json
import os
import signal
import subprocess
from collections import defaultdict
from collections import deque
from collections import namedtuple
from datetime import datetime
from itertools import count
from itertools import groupby
from threading import Thread
from time import sleep
from time import time

import attr
import pytest
import zmq
from _pytest import runner

from cfme.fixtures import terminalreporter
from cfme.fixtures.parallelizer import remote
from cfme.fixtures.pytest_store import store
from cfme.test_framework.appliance import PLUGIN_KEY as APPLIANCE_PLUGIN
from cfme.utils import at_exit
from cfme.utils import conf
from cfme.utils.log import create_sublogger

# Initialize slaveid to None, indicating this as the master process
# slaves will set this to a unique string when they're initialized
conf.runtime['env']['slaveid'] = None

if not conf.runtime['env'].get('ts'):
    ts = str(time())
    conf.runtime['env']['ts'] = ts


def pytest_addhooks(pluginmanager):
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


@pytest.mark.trylast
def pytest_configure(config):
    """Configures the parallel session, then fires pytest_parallel_configured."""
    if config.getoption('--help'):
        return

    reporter = terminalreporter.reporter()
    holder = config.pluginmanager.get_plugin(APPLIANCE_PLUGIN)

    appliances = holder.appliances

    if len(appliances) > 1:
        session = ParallelSession(config, appliances)
        config.pluginmanager.register(session, "parallel_session")
        store.parallelizer_role = 'master'
        reporter.write_line(
            'As a parallelizer master kicking off parallel session for these {} appliances'.format(
                len(appliances)),
            green=True)
        config.hook.pytest_parallel_configured(parallel_session=session)
    else:
        reporter.write_line('No parallelization required', green=True)
        config.hook.pytest_parallel_configured(parallel_session=None)


def handle_end_session(signal, frame):
    # when signaled, end the current test session immediately
    if store.parallel_session:
        store.parallel_session.session_finished = True


signal.signal(signal.SIGQUIT, handle_end_session)


@attr.s(hash=False)
class SlaveDetail(object):

    slaveid_generator = ('slave{:02d}'.format(i).encode('ascii') for i in count())

    appliance = attr.ib()
    worker_config = attr.ib()
    id = attr.ib(default=attr.Factory(
        lambda: next(SlaveDetail.slaveid_generator)))
    forbid_restart = attr.ib(default=False, init=False)
    tests = attr.ib(default=attr.Factory(set), repr=False)
    process = attr.ib(default=None, repr=False)

    provider_allocation = attr.ib(default=attr.Factory(list), repr=False)

    def start(self):
        if self.forbid_restart:
            return
        devnull = open(os.devnull, 'w')
        # worker output redirected to null; useful info comes via messages and logs
        self.process = subprocess.Popen([
            'python', remote.__file__,
            '--worker', self.id,
            '--appliance', self.appliance.as_json,
            '--ts', conf.runtime['env']['ts'],
            '--config', json.dumps(self.worker_config)

        ], stdout=devnull)
        at_exit(self.process.kill)

    def poll(self):
        if self.process is not None:
            return self.process.poll()


class ParallelSession(object):
    def __init__(self, config, appliances):
        self.config = config
        self.session = None
        self.session_finished = False
        self.countfailures = 0
        self.collection = []
        self.sent_tests = 0
        self.log = create_sublogger('master')
        self.maxfail = config.getvalue("maxfail")
        self._failed_collection_errors = {}
        self.terminal = store.terminalreporter
        self.trdist = None
        self.slaves = {}
        self.test_groups = self._test_item_generator()

        self._pool = []

        # necessary to get list of supported providers
        version = appliances[0].version
        from cfme.markers.env_markers.provider import all_required
        self.provs = sorted([p.the_id for p in all_required(version, filters=[])],
                            key=len, reverse=True)
        self.used_prov = set()

        self.failed_slave_test_groups = deque()
        self.slave_spawn_count = 0
        self.appliances = appliances

        # set up the ipc socket

        zmq_endpoint = 'ipc://{}'.format(
            config.cache.makedir('parallelize').join(str(os.getpid())))
        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.ROUTER)
        self.sock.bind(zmq_endpoint)

        # clean out old slave config if it exists

        self.worker_config = {
            'args': self.config.args,
            'options': dict(  # copy to avoid aliasing
                vars(self.config.option),
                use_sprout=False,   # Slaves don't use sprout
            ),
            'zmq_endpoint': zmq_endpoint,
            'appliance_data': getattr(self, "slave_appliances_data", {})
        }

        for appliance in self.appliances:
            slave_data = SlaveDetail(appliance=appliance, worker_config=self.worker_config)
            self.slaves[slave_data.id] = slave_data

        for slave in sorted(self.slaves):
            self.print_message("using appliance {}".format(self.slaves[slave].appliance.url),
                slave, green=True)

    def _slave_audit(self):
        # XXX: There is currently no mechanism to add or remove slave_urls, short of
        #      firing up the debugger and doing it manually. This is making room for
        #      planned future abilities to dynamically add and remove slaves via automation

        # check for unexpected slave shutdowns and redistribute tests
        for slave in self.slaves.values():
            returncode = slave.poll()
            if returncode:
                slave.process = None
                if returncode == -9:
                    msg = '{} killed due to error, respawning'.format(slave.id)
                else:
                    msg = '{} terminated unexpectedly with status {}, respawning'.format(
                        slave.id, returncode)
                if slave.tests:
                    failed_tests, slave.tests = slave.tests, set()
                    num_failed_tests = len(failed_tests)
                    self.sent_tests -= num_failed_tests
                    msg += ' and redistributing {} tests'.format(num_failed_tests)
                    self.failed_slave_test_groups.append(failed_tests)
                self.print_message(msg, purple=True)

        # If a slave was terminated for any reason, kill that slave
        # the terminated flag implies the appliance has died :(
        for slave in self.slaves.values():
            if slave.forbid_restart:
                if slave.process is None:
                    self.config.hook.pytest_miq_node_shutdown(
                        config=self.config, nodeinfo=slave.appliance.url)
                    del self.slaves[slave.id]
                else:
                    # no hook call here, a future audit will handle the fallout
                    self.print_message(
                        "{}'s appliance has died, deactivating slave".format(slave.id))
                    self.interrupt(slave)
            else:
                if slave.process is None:
                    slave.start()
                    self.slave_spawn_count += 1

    def send(self, slave, event_data):
        """Send data to slave.

        ``event_data`` will be serialized as JSON, and so must be JSON serializable

        """
        event_json = json.dumps(event_data)
        if not isinstance(event_json, bytes):
            event_json = event_json.encode('utf-8')
        self.sock.send_multipart([slave.id, b'', event_json])

    def recv(self):
        # poll the zmq socket, populate the recv queue deque with responses

        events = zmq.zmq_poll([(self.sock, zmq.POLLIN)], 50)
        if not events:
            return None, None, None
        slaveid, _, event_json = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        event_data = json.loads(event_json)
        event_name = event_data.pop('_event_name')
        if slaveid not in self.slaves:
            self.log.error("message from terminated worker %s %s %s",
                           slaveid, event_name, event_data)
            return None, None, None
        return self.slaves[slaveid], event_data, event_name

    def print_message(self, message, prefix='master', **markup):
        """Print a message from a node to the py.test console

        Args:
            message: The message to print
            **markup: If set, overrides the default markup when printing the message

        """
        # differentiate master and slave messages by default
        prefix = getattr(prefix, 'id', prefix)
        if not isinstance(prefix, str):
            prefix = prefix.decode('ascii')
        if not markup:
            if prefix == 'master':
                markup = {'blue': True}
            else:
                markup = {'cyan': True}
        stamp = datetime.now().strftime("%Y%m%d %H:%M:%S")
        self.terminal.write_ensure_prefix(
            '({})[{}] '.format(prefix, stamp), message, **markup)

    def ack(self, slave, event_name):
        """Acknowledge a slave's message"""
        self.send(slave, 'ack {}'.format(event_name))

    def monitor_shutdown(self, slave):
        # non-daemon so slaves get every opportunity to shut down cleanly
        shutdown_thread = Thread(target=self._monitor_shutdown_t,
                                 args=(slave.id, slave.process))
        shutdown_thread.start()

    def _monitor_shutdown_t(self, slaveid, process):
        # a KeyError here means self.slaves got mangled, indicating a problem elsewhere
        if process is None:
            self.log.warning('Slave was missing when trying to monitor shutdown')

        def sleep_and_poll():
            start_time = time()

            # configure the polling logic
            polls = 0
            # how often to poll
            poll_sleep_time = .5
            # how often to report (calculated to be around once a minute based on poll_sleep_time)
            poll_report_modulo = 60 / poll_sleep_time
            # maximum time to wait
            poll_num_sec = 300

            while (time() - start_time) < poll_num_sec:
                polls += 1
                yield
                if polls % poll_report_modulo == 0:
                    remaining_time = int(poll_num_sec - (time() - start_time))
                    self.print_message('{} shutting down, will continue polling for {} seconds'
                                       .format(slaveid.decode('ascii'), remaining_time),
                                       blue=True)
                sleep(poll_sleep_time)

        # start the poll
        for _ in sleep_and_poll():
            ec = process.poll()
            if ec is None:
                continue
            else:
                if ec == 0:
                    self.print_message('{} exited'.format(slaveid), green=True)
                else:
                    self.print_message('{} died'.format(slaveid), red=True)
                break
        else:
            self.print_message('{} failed to shut down gracefully; killed'.format(slaveid),
                red=True)
            process.kill()

    def interrupt(self, slave, **kwargs):
        """Nicely ask a slave to terminate"""
        slave.forbid_restart = True
        if slave.poll() is None:
            slave.process.send_signal(subprocess.signal.SIGINT)
            self.monitor_shutdown(slave, **kwargs)

    def kill(self, slave, **kwargs):
        """Rudely kill a slave"""
        slave.forbid_restart = True
        if slave.poll() is None:
            slave.process.kill()
            self.monitor_shutdown(slave, **kwargs)

    def send_tests(self, slave):
        """Send a slave a group of tests"""
        try:
            tests = list(self.failed_slave_test_groups.popleft())
        except IndexError:
            tests = self.get(slave)
        self.send(slave, tests)
        slave.tests.update(tests)
        collect_len = len(self.collection)
        tests_len = len(tests)
        self.sent_tests += tests_len
        if tests:
            self.print_message('sent {} tests to {} ({}/{}, {:.1f}%)'.format(
                tests_len, slave.id, self.sent_tests, collect_len,
                self.sent_tests * 100. / collect_len
            ))
        return tests

    def pytest_sessionstart(self, session):
        """pytest sessionstart hook

        - sets up distributed terminal reporter
        - sets up zmp ipc socket for the slaves to use
        - writes pytest options and args to worker_config.yaml
        - starts the slaves
        - register atexit kill hooks to destroy slaves at the end if things go terribly wrong

        """
        # If reporter() gave us a fake terminal reporter in __init__, the real
        # terminal reporter is registered by now
        self.terminal = store.terminalreporter
        self.trdist = TerminalDistReporter(self.config, self.terminal)
        self.config.pluginmanager.register(self.trdist, "terminaldistreporter")
        self.session = session

    def pytest_runtestloop(self):
        """pytest runtest loop

        - Disable the master terminal reporter hooks, so we can add our own handlers
          that include the slaveid in the output
        - Send tests to slaves when they ask
        - Log the starting of tests and test results, including slave id
        - Handle clean slave shutdown when they finish their runtest loops
        - Restore the master terminal reporter after testing so we get the final report

        """
        # Build master collection for slave diffing and distribution
        self.collection = [item.nodeid for item in self.session.items]

        # Fire up the workers after master collection is complete
        # master and the first slave share an appliance, this is a workaround to prevent a slave
        # from altering an appliance while master collection is still taking place
        for slave in self.slaves.values():
            slave.start()

        try:
            self.print_message("Waiting for {} slave collections".format(len(self.slaves)),
                red=True)

            # Turn off the terminal reporter to suppress the builtin logstart printing
            terminalreporter.disable()

            while True:
                # spawn/kill/replace slaves if needed
                self._slave_audit()

                if not self.slaves:
                    # All slaves are killed or errored, we're done with tests
                    self.print_message('all slaves have exited', yellow=True)
                    self.session_finished = True

                if self.session_finished:
                    break

                slave, event_data, event_name = self.recv()
                if event_name == 'message':
                    message = event_data.pop('message')
                    markup = event_data.pop('markup')
                    # messages are special, handle them immediately
                    self.print_message(message, slave, **markup)
                    self.ack(slave, event_name)
                elif event_name == 'collectionfinish':
                    slave_collection = event_data['node_ids']
                    # compare slave collection to the master, all test ids must be the same
                    self.log.debug('diffing {} collection'.format(slave.id))
                    diff_err = report_collection_diff(
                        slave.id, self.collection, slave_collection)
                    if diff_err:
                        self.print_message(
                            'collection differs, respawning', slave.id,
                            purple=True)
                        self.print_message(diff_err, purple=True)
                        self.log.error('{}'.format(diff_err))
                        self.kill(slave)
                        slave.start()
                    else:
                        self.ack(slave, event_name)
                elif event_name == 'need_tests':
                    self.send_tests(slave)
                    self.log.info('starting master test distribution')
                elif event_name == 'runtest_logstart':
                    self.ack(slave, event_name)
                    self.trdist.runtest_logstart(
                        slave.id,
                        event_data['nodeid'],
                        event_data['location'])
                elif event_name == 'runtest_logreport':
                    self.ack(slave, event_name)
                    report = unserialize_report(event_data['report'])
                    if report.when in ('call', 'teardown'):
                        slave.tests.discard(report.nodeid)
                    self.trdist.runtest_logreport(slave.id, report)
                elif event_name == 'internalerror':
                    self.ack(slave, event_name)
                    self.print_message(event_data['message'], slave, purple=True)
                    self.kill(slave)
                elif event_name == 'shutdown':
                    self.config.hook.pytest_miq_node_shutdown(
                        config=self.config, nodeinfo=slave.appliance.url)
                    self.ack(slave, event_name)
                    del self.slaves[slave.id]
                    self.monitor_shutdown(slave)

                # total slave spawn count * 3, to allow for each slave's initial spawn
                # and then each slave (on average) can fail two times
                if self.slave_spawn_count >= len(self.appliances) * 3:
                    self.print_message(
                        'too many slave respawns, exiting',
                        red=True, bold=True)
                    raise KeyboardInterrupt('Interrupted due to slave failures')
        except Exception as ex:
            self.log.error('Exception in runtest loop:')
            self.log.exception(ex)
            self.print_message(str(ex))
            raise
        finally:
            terminalreporter.enable()

        # Suppress other runtestloop calls
        return True

    def _test_item_generator(self):
        for tests in self._modscope_item_generator():
            yield tests

    def _modscope_item_generator(self):
        # breaks out tests by module, can work just about any way we want
        # as long as it yields lists of tests id from the master collection
        sent_tests = 0
        collection_len = len(self.collection)

        def get_fspart(nodeid):
            return nodeid.split('::')[0]

        for fspath, gen_moditems in groupby(self.collection, key=get_fspart):
            for tests in self._modscope_id_splitter(gen_moditems):
                sent_tests += len(tests)
                self.log.info('{} tests remaining to send'.format(
                    collection_len - sent_tests))
                yield list(tests)

    def _modscope_id_splitter(self, module_items):
        # given a list of item ids from one test module, break up tests into groups with the same id
        parametrized_ids = defaultdict(list)
        for item in module_items:
            if '[' in item:
                # split on the leftmost bracket, then strip everything after the rightmight bracket
                # so 'test_module.py::test_name[parametrized_id]' becomes 'parametrized_id'
                parametrized_id = item.split('[')[1].rstrip(']')
            else:
                # splits failed, item has no parametrized id
                parametrized_id = 'no params'
            parametrized_ids[parametrized_id].append(item)

        for id, tests in parametrized_ids.items():
            if tests:
                self.log.info('sent tests with param {} {!r}'.format(id, tests))
                yield tests

    def get(self, slave):

        # we assume that there is only one provider of the same type and version
        # because there is no better way to group tests w/o provider initialization
        def provs_of_tests(test_group):
            found = set()
            for test in test_group:
                found.update(pv for pv in self.provs
                             if '[' in test and pv in test)
            return sorted(found)

        if not self._pool:
            for test_group in self.test_groups:
                self._pool.append(test_group)
                self.used_prov.update(provs_of_tests(test_group))
            if self.used_prov:
                self.ratio = float(len(self.slaves)) / len(self.used_prov)
            else:
                self.ratio = 0.0
        if not self._pool:
            return []
        appliance_num_limit = 1
        for idx, test_group in enumerate(self._pool):
            provs = provs_of_tests(test_group)
            if provs:
                prov = provs[0]
                if prov in slave.provider_allocation:
                    # provider is already with the slave, so just return the tests
                    self._pool.remove(test_group)
                    return test_group
                else:
                    if len(slave.provider_allocation) >= appliance_num_limit:
                        continue
                    else:
                        # Adding provider to slave since there are not too many
                        slave.provider_allocation.append(prov)
                        self._pool.remove(test_group)
                        return test_group
            else:
                # No providers - ie, not a provider parametrized test
                # or no params, so not parametrized at all
                self._pool.remove(test_group)
                return test_group

        # Here means no tests were able to be sent
        for test_group in self._pool:

            provs = provs_of_tests(test_group)
            if provs:
                prov = provs[0]
                # Already too many slaves with provider
                app = slave.appliance
                self.print_message('removing providers from appliance', slave, purple=True)
                try:
                    app.delete_all_providers()
                except Exception as e:
                    self.print_message('exception during provider removal: {}'.format(e),
                                       slave,
                                       red=True)
            slave.provider_allocation = [prov]
            self._pool.remove(test_group)
            return test_group
        assert not self._pool, self._pool
        return []


def report_collection_diff(slaveid, from_collection, to_collection):
    """Report differences, if any exist, between master and a slave collection

    Raises RuntimeError if collections differ

    Note:

        This function will sort functions before comparing them.

    """
    from_collection, to_collection = sorted(from_collection), sorted(to_collection)
    if from_collection == to_collection:
        # Well, that was easy.
        return

    # diff the two, so we get some idea of what's wrong
    diff = difflib.unified_diff(
        from_collection,
        to_collection,
        fromfile='master',
        tofile=slaveid,
    )

    # diff is a line generator, stringify it
    diff = '\n'.join([line.rstrip() for line in diff])
    return '{slaveid} diff:\n{diff}\n'.format(slaveid=slaveid, diff=diff)


class TerminalDistReporter(object):
    """Terminal Reporter for Distributed Testing

    trdist reporter exists to make sure we get good distributed logging during the runtest loop,
    which means the normal terminal reporter should be disabled during the loop

    This class is where we make sure the terminal reporter is made aware of whatever state it
    needs to report properly once we turn it back on after the runtest loop

    It has special versions of pytest reporting hooks that, where possible, try to include a
    slave ID. These hooks are called in :py:class:`ParallelSession`'s runtestloop hook.

    """
    def __init__(self, config, terminal):
        self.config = config
        self.tr = terminal
        self.outcomes = {}

    def runtest_logstart(self, slaveid, nodeid, location):
        test = self.tr._locationline(nodeid, *location)
        prefix = '({}) {}'.format(slaveid, test)
        self.tr.write_ensure_prefix(prefix, 'running', blue=True)
        self.config.hook.pytest_runtest_logstart(nodeid=nodeid, location=location)

    def runtest_logreport(self, slaveid, report):
        # Run all the normal logreport hooks
        self.config.hook.pytest_runtest_logreport(report=report)

        # Now do what the terminal reporter would normally do, but include parallelizer info
        outcome, letter, word = self.config.hook.pytest_report_teststatus(report=report)
        # Stash stats on the terminal reporter so it reports properly
        # after it's reenabled at the end of runtestloop
        self.tr.stats.setdefault(outcome, []).append(report)
        test = self.tr._locationline(report.nodeid, *report.location)

        prefix = '({}) {}'.format(slaveid, test)
        try:
            # for some reason, pytest_report_teststatus returns a word, markup tuple
            # when the word would be 'XPASS', so unpack it here if that's the case
            word, markup = word
        except (TypeError, ValueError):
            # word wasn't iterable or didn't have enough values, use it as-is
            pass

        if word in ('PASSED', 'xfail'):
            markup = {'green': True}
        elif word in ('ERROR', 'FAILED', 'XPASS'):
            markup = {'red': True}
        elif word:
            markup = {'yellow': True}

        # For every stage where we can report the outcome, stash it in the outcomes dict
        if word:
            self.outcomes[test] = Outcome(word, markup)

        # Then, when we get to the teardown report, print the last outcome
        # This prevents reportings a test as 'PASSED' if its teardown phase fails, for example
        if report.when == 'teardown':
            word, markup = self.outcomes.pop(test)
            self.tr.write_ensure_prefix(prefix, word, **markup)


Outcome = namedtuple('Outcome', ['word', 'markup'])


def unserialize_report(reportdict):
    """
    Generate a :py:class:`TestReport <pytest:_pytest.runner.TestReport>` from a serialized report
    """
    return runner.TestReport(**reportdict)
