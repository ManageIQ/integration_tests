"""Parallel testing, supporting arbitrary collection ordering

The Workflow
------------

- Master py.test process starts up, inspects config to decide how many slave to start, if at all

  - env['parallel_base_urls'] is inspected first
  - py.test config.option.appliances and the related --appliance cmdline flag are used
    if env['parallel_base_urls'] isn't set
  - if neither are set, no parallelization happens

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

import collections
import difflib
import json
import os
import signal
import subprocess
from collections import OrderedDict, defaultdict, deque, namedtuple
from datetime import datetime
from itertools import count

from threading import Thread
from time import sleep, time
from urlparse import urlparse

import pytest
import zmq
from _pytest import runner

from fixtures import terminalreporter
from fixtures.parallelizer import remote
from fixtures.pytest_store import store
from utils import at_exit, conf
from utils.appliance import IPAppliance
from utils.log import create_sublogger
from utils.path import conf_path

# Initialize slaveid to None, indicating this as the master process
# slaves will set this to a unique string when they're initialized
conf.runtime['env']['slaveid'] = None

if not conf.runtime['env'].get('ts'):
    ts = str(time())
    conf.runtime['env']['ts'] = ts


def pytest_addhooks(pluginmanager):
    import hooks
    pluginmanager.add_hookspecs(hooks)


@pytest.mark.trylast
def pytest_configure(config):
    # configures the parallel session, then fires pytest_parallel_configured
    if len(config.option.appliances) > 1:
        session = ParallelSession(config)
        config.pluginmanager.register(session, "parallel_session")
        store.parallelizer_role = 'master'
        config.hook.pytest_parallel_configured(parallel_session=session)
    else:
        config.hook.pytest_parallel_configured(parallel_session=None)


def handle_end_session(signal, frame):
    # when signaled, end the current test session immediately
    if store.parallel_session:
        store.parallel_session.session_finished = True


signal.signal(signal.SIGQUIT, handle_end_session)


class SlaveDict(dict):
    """A normal dict, but with a special "add" method that autogenerated slaveids"""
    # intentionally in the class scope so all instances share the slave counter
    slaveid_generator = ('slave{:02d}'.format(i) for i in count())
    _instances = []

    def __init__(self, *args, **kwargs):
        super(SlaveDict, self).__init__(*args, **kwargs)
        SlaveDict._instances.append(self)

    # autoincrement the slaveids when something is added
    def add(self, value):
        self[next(self.slaveid_generator)] = value

    # when removing a slave with this method, it is removed from all instances
    # use the normal `del` behavior to only remove from one instances
    def remove(self, key):
        for instance in self._instances:
            instance.pop(key, None)


class ParallelSession(object):
    def __init__(self, config):
        self.config = config
        self.session = None
        self.session_finished = False
        self.countfailures = 0
        self.collection = OrderedDict()
        self.sent_tests = 0
        self.log = create_sublogger('master')
        self.maxfail = config.getvalue("maxfail")
        self._failed_collection_errors = {}
        self.terminal = store.terminalreporter
        self.trdist = None
        self.slaves = SlaveDict()
        self.slave_urls = SlaveDict()
        self.slave_tests = defaultdict(set)
        self.test_groups = self._test_item_generator()

        self._pool = []
        from utils.conf import cfme_data
        self.provs = sorted(set(cfme_data['management_systems'].keys()),
                            key=len, reverse=True)
        self.slave_allocation = collections.defaultdict(list)
        self.used_prov = set()

        self.failed_slave_test_groups = deque()
        self.slave_spawn_count = 0
        self.appliances = self.config.option.appliances

        # set up the ipc socket

        zmq_endpoint = 'ipc://{}'.format(
            config.cache.makedir('parallelize').join(str(os.getpid())))
        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.ROUTER)
        self.sock.bind(zmq_endpoint)

        # clean out old slave config if it exists
        slave_config = conf_path.join('slave_config.yaml')
        slave_config.check() and slave_config.remove()

        # write out the slave config
        conf.runtime['slave_config'] = {
            'args': self.config.args,
            'options': self.config.option.__dict__,
            'zmq_endpoint': zmq_endpoint,
        }
        if hasattr(self, "slave_appliances_data"):
            conf.runtime['slave_config']["appliance_data"] = self.slave_appliances_data
        conf.runtime['slave_config']['options']['use_sprout'] = False  # Slaves don't use sprout
        conf.save('slave_config')

        for base_url in self.appliances:
            self.slave_urls.add(base_url)

        for slave in sorted(self.slave_urls):
            self.print_message("using appliance {}".format(self.slave_urls[slave]),
                slave, green=True)

    def _slave_audit(self):
        # XXX: There is currently no mechanism to add or remove slave_urls, short of
        #      firing up the debugger and doing it manually. This is making room for
        #      planned future abilities to dynamically add and remove slaves via automation

        # check for unexpected slave shutdowns and redistribute tests
        for slaveid, slave in self.slaves.items():
            returncode = slave.poll()
            if returncode:
                del(self.slaves[slaveid])
                if returncode == -9:
                    msg = '{} killed due to error, respawning'.format(slaveid)
                else:
                    msg = '{} terminated unexpectedly with status {}, respawning'.format(
                        slaveid, returncode)
                if self.slave_tests[slaveid]:
                    num_failed_tests = len(self.slave_tests[slaveid])
                    self.sent_tests -= num_failed_tests
                    msg += ' and redistributing {} tests'.format(num_failed_tests)
                    self.failed_slave_test_groups.append(self.slave_tests.pop(slaveid))
                self.print_message(msg, purple=True)

        # Make sure we have a slave for every slave_url
        for slaveid in list(self.slave_urls):
            if slaveid not in self.slaves:
                self._start_slave(slaveid)

        # If a slave has lost its base_url for any reason, kill that slave
        # Losing a base_url means the associated appliance died :(
        for slaveid in list(self.slaves):
            if slaveid not in self.slave_urls:
                self.print_message("{}'s appliance has died, deactivating slave".format(slaveid))
                self.interrupt(slaveid)

    def _start_slave(self, slaveid):
        devnull = open(os.devnull, 'w')
        try:
            base_url = self.slave_urls[slaveid]
        except KeyError:
            # race condition: slave was removed from slave_urls when something else decided to
            # start it; in this case slave_urls wins and the slave should not start
            return

        # worker output redirected to null; useful info comes via messages and logs
        slave = subprocess.Popen(
            ['python', remote.__file__, slaveid, base_url, conf.runtime['env']['ts']],
            stdout=devnull,
        )
        self.slaves[slaveid] = slave
        self.slave_spawn_count += 1
        at_exit(slave.kill)

    def send(self, slaveid, event_data):
        """Send data to slave.

        ``event_data`` will be serialized as JSON, and so must be JSON serializable

        """
        event_json = json.dumps(event_data)
        self.sock.send_multipart([slaveid, '', event_json])

    def recv(self):
        # poll the zmq socket, populate the recv queue deque with responses

        events = zmq.zmq_poll([(self.sock, zmq.POLLIN)], 500)
        if not events:
            return None, None, None
        slaveid, _, event_json = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        event_data = json.loads(event_json)
        event_name = event_data.pop('_event_name')
        return slaveid, event_data, event_name

    def print_message(self, message, prefix='master', **markup):
        """Print a message from a node to the py.test console

        Args:
            slaveid: Can be a slaveid or any string, e.g. ``'master'`` is also useful here.
            message: The message to print
            **markup: If set, overrides the default markup when printing the message

        """
        # differentiate master and slave messages by default
        if not markup:
            if prefix == 'master':
                markup = {'blue': True}
            else:
                markup = {'cyan': True}
        stamp = datetime.now().strftime("%Y%m%d %H:%M:%S")
        self.terminal.write_ensure_prefix('({})[{}] '.format(prefix, stamp), message, **markup)

    def ack(self, slaveid, event_name):
        """Acknowledge a slave's message"""
        self.send(slaveid, 'ack {}'.format(event_name))

    def monitor_shutdown(self, slaveid, respawn=False):
        # non-daemon so slaves get every opportunity to shut down cleanly
        shutdown_thread = Thread(target=self._monitor_shutdown_t,
                                 args=(slaveid, respawn))
        shutdown_thread.start()

    def _monitor_shutdown_t(self, slaveid, respawn):
        # a KeyError here means self.slaves got mangled, indicating a problem elsewhere
        try:
            slave = self.slaves[slaveid]
        except KeyError:
            self.log.warning('Slave was missing when trying to monitor shutdown')
            return

        start_time = time()

        # configure the polling logic
        polls = 0
        # how often to poll
        poll_sleep_time = .5
        # how often to report (calculated to be around once a minute based on poll_sleep_time)
        poll_report_modulo = 60 / poll_sleep_time
        # maximum time to wait
        poll_num_sec = 300

        # time spent waiting
        def poll_walltime():
            return time() - start_time

        # start the poll
        while poll_walltime() < poll_num_sec:
            polls += 1
            ec = slave.poll()
            if ec is None:
                # process still running, report if needed and continue polling
                if polls % poll_report_modulo == 0:
                    remaining_time = int(poll_num_sec - poll_walltime())
                    self.print_message('{} still shutting down, '
                        'will continue polling for {} seconds '
                        .format(slaveid, remaining_time), blue=True)
            else:
                if ec == 0:
                    self.print_message('{} exited'.format(slaveid), green=True)
                else:
                    self.print_message('{} died'.format(slaveid), red=True)
                break
            sleep(poll_sleep_time)
        else:
            self.print_message('{} failed to shut down gracefully; killed'.format(slaveid),
                red=True)
            slave.kill()
        # todo: race conditions here, use messages
        if not respawn and slaveid in self.slave_urls:
            self.slave_urls.remove(slaveid)
        elif slaveid in self.slaves:
            del(self.slaves[slaveid])

    def interrupt(self, slaveid, **kwargs):
        """Nicely ask a slave to terminate"""
        slave = self.slaves.pop(slaveid, None)
        if slave and slave.poll() is None:
            slave.send_signal(subprocess.signal.SIGINT)
            self.monitor_shutdown(slaveid, **kwargs)

    def kill(self, slaveid, **kwargs):
        """Rudely kill a slave"""
        slave = self.slaves.pop(slaveid, None)
        if slave and slave.poll() is None:
            slave.kill()
            self.monitor_shutdown(slaveid, **kwargs)

    def send_tests(self, slaveid):
        """Send a slave a group of tests"""
        try:
            tests = list(self.failed_slave_test_groups.popleft())
        except IndexError:
            try:
                tests = self.get(slaveid)
                # To return to the old parallelizer distributor, remove the line above
                # and replace it with the line below.
                # tests = self.test_groups.next()
            except StopIteration:
                tests = []
        tests = tests or []
        self.send(slaveid, tests)
        self.slave_tests[slaveid] |= set(tests)
        collect_len = len(self.collection)
        tests_len = len(tests)
        self.sent_tests += tests_len
        if tests:
            self.print_message('sent {} tests to {} ({}/{}, {:.1f}%)'.format(
                tests_len, slaveid, self.sent_tests, collect_len,
                self.sent_tests * 100. / collect_len
            ))
        return tests

    def pytest_sessionstart(self, session):
        """pytest sessionstart hook

        - sets up distributed terminal reporter
        - sets up zmp ipc socket for the slaves to use
        - writes pytest options and args to slave_config.yaml
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
        self._slave_audit()

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

                slaveid, event_data, event_name = self.recv()
                if event_name == 'message':
                    message = event_data.pop('message')
                    markup = event_data.pop('markup')
                    # messages are special, handle them immediately
                    self.print_message(message, slaveid, **markup)
                    self.ack(slaveid, event_name)
                elif event_name == 'collectionfinish':
                    slave_collection = event_data['node_ids']
                    # compare slave collection to the master, all test ids must be the same
                    self.log.debug('diffing {} collection'.format(slaveid))
                    diff_err = report_collection_diff(
                        slaveid, self.collection, slave_collection)
                    if diff_err:
                        self.print_message('collection differs, respawning', slaveid,
                            purple=True)
                        self.print_message(diff_err, purple=True)
                        self.log.error('{}'.format(diff_err))
                        self.kill(slaveid)
                        self._start_slave(slaveid)
                    else:
                        self.ack(slaveid, event_name)
                elif event_name == 'need_tests':
                    self.send_tests(slaveid)
                    self.log.info('starting master test distribution')
                elif event_name == 'runtest_logstart':
                    self.ack(slaveid, event_name)
                    self.trdist.runtest_logstart(slaveid,
                        event_data['nodeid'], event_data['location'])
                elif event_name == 'runtest_logreport':
                    self.ack(slaveid, event_name)
                    report = unserialize_report(event_data['report'])
                    if report.when in ('call', 'teardown'):
                        self.slave_tests[slaveid].discard(report.nodeid)
                    self.trdist.runtest_logreport(slaveid, report)
                elif event_name == 'internalerror':
                    self.ack(slaveid, event_name)
                    self.print_message(event_data['message'], slaveid, purple=True)
                    with SlaveDict.lock:
                        if slaveid in self.slaves:
                            # If this slave hasn't already quit, kill it with fire (signal 9)
                            self.slaves[slaveid].send_signal(9)
                elif event_name == 'shutdown':
                    self.ack(slaveid, event_name)
                    self.monitor_shutdown(slaveid)

                # total slave spawn count * 3, to allow for each slave's initial spawn
                # and then each slave (on average) can fail two times
                if self.slave_spawn_count >= len(self.appliances) * 3:
                    self.print_message('too many slave respawns, exiting',
                        red=True, bold=True)
                    raise KeyboardInterrupt('Interrupted due to slave failures')
        except Exception as ex:
            self.log.error('Exception in runtest loop:')
            self.log.exception(ex)
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

        def get_fspart(nodeid):
            return nodeid.split('::')[0]

        for fspath, gen_moditems in group_by(self.collection, key=get_fspart):
            for tests in self._modscope_id_splitter(gen_moditems):
                sent_tests += len(tests)
                self.log.info('%d tests remaining to send'
                              % (collection_len - sent_tests))
                    yield tests


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
        if not self._pool:
            for test_group in self.test_groups:
                self._pool.append(test_group)
                for test in test_group:
                    if '[' in test:
                        found_prov = []
                        for pv in self.provs:
                            if pv in test:
                                found_prov.append(pv)
                                break
                        provs = list(set(found_prov).intersection(self.provs))
                        if provs:
                            self.used_prov = self.used_prov.union(set(provs))
            if self.used_prov:
                self.ratio = float(len(self.slaves)) / float(len(self.used_prov))
            else:
                self.ratio = 0.0
            if not self._pool:
                return []
            current_allocate = self.slave_allocation.get(slave, None)
            # num_provs_list = [len(v) for k, v in self.slave_allocation.iteritems()]
            # average_num_provs = sum(num_provs_list) / float(len(self.slaves))
            appliance_num_limit = 1
            for test_group in self._pool:
                for test in test_group:
                    # If the test is parametrized...
                    if '[' in test:
                        found_prov = []
                        for pv in self.provs:
                            if pv in test:
                                found_prov.append(pv)
                                break
                        # The line below can probably be removed now, since we compare
                        # providers in the loop above with self.provs, which is a list
                        # of all providers.
                        provs = list(set(found_prov).intersection(self.provs))
                        # If the parametrization contains a provider...
                        if provs:
                            prov = provs[0]
                            # num_slave_with_prov = len([sl for sl, provs_list
                            #    in self.slave_allocation.iteritems()
                            #    if prov in provs_list])
                            # If this slave/appliance already has providers then...
                            if current_allocate:
                                # If the slave has _our_ provider
                                if prov in current_allocate:
                                    # provider is already with the slave, so just return the tests
                                    self._pool.remove(test_group)
                                    return test_group
                                # If the slave doesn't have _our_ provider
                                else:
                                    # Check to see how many slaves there are with this provider
                                    if len(self.slave_allocation[slave]) >= appliance_num_limit:
                                        continue
                                    else:
                                        # Adding provider to slave since there are not too many
                                        self.slave_allocation[slave].append(prov)
                                        self._pool.remove(test_group)
                                        return test_group
                            # If this slave doesn't have any providers...
                            else:
                                # Adding provider to slave
                                self.slave_allocation[slave].append(prov)
                                self._pool.remove(test_group)
                                return test_group
                        else:
                            # No providers - ie, not a provider parametrized test
                            self._pool.remove(test_group)
                            return test_group
                    else:
                        # No params, so no need to think about providers
                        self._pool.remove(test_group)
                        return test_group
                # Here means no tests were able to be sent
            for test_group in self._pool:
                for test in test_group:
                    # If the test is parametrized...
                    if '[' in test:
                        found_prov = []
                        for pv in self.provs:
                            if pv in test:
                                found_prov.append(pv)
                                break
                        # The line below can probably be removed now, since we compare
                        # providers in the loop above with self.provs, which is a list
                        # of all providers.
                        provs = list(set(found_prov).intersection(self.provs))
                        # If the parametrization contains a provider...
                        if provs:
                            # Already too many slaves with provider
                            app_url = self.slave_urls[slave]
                            app_ip = urlparse(app_url).netloc
                            app = IPAppliance(app_ip)
                            self.print_message('cleansing appliance', slave,
                                purple=True)
                            try:
                                app.delete_all_providers()
                            except:
                                self.print_message('cloud not cleanse', slave,
                                red=True)
                            self.slave_allocation[slave] = [prov]
                            self._pool.remove(test_group)
                            return test_group
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
