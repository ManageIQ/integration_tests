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

import atexit
import difflib
import json
import os
import subprocess
from collections import OrderedDict, defaultdict, namedtuple

import pytest
import zmq
from _pytest import runner

from fixtures.parallelizer import remote
from fixtures.terminalreporter import reporter
from utils import conf
from utils.log import create_sublogger


_appliance_help = '''specify appliance URLs to use for distributed testing.
this option can be specified more than once, and must be specified at least two times'''

env_base_urls = conf.env.get('parallel_base_urls', [])
if env_base_urls:
    conf.runtime['env']['base_url'] = env_base_urls[0]

# Initialize slaveid to None, indicating this as the master process
# slaves will set this to a unique string when they're initialized
conf.runtime['env']['slaveid'] = None


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group._addoption('--appliance', dest='appliances', action='append',
        default=env_base_urls, metavar='base_url', help=_appliance_help)


def pytest_configure(config, __multicall__):
    __multicall__.execute()
    # TODO: Wrap in a conditional based on the number of appliances for testing
    if config.option.appliances:
        session = ParallelSession(config)
        config.pluginmanager.register(session, "parallel_session")


def _failsafe(kill_func):
    # atexit hook for killing a slave
    # slave should probably already be dead, this is just a last-ditch catchall
    try:
        kill_func()
    except:
        pass


class ParallelSession(object):
    def __init__(self, config):
        self.config = config
        self.session = None
        self.countfailures = 0
        self.collection = OrderedDict()
        self.log = create_sublogger('master')
        self.maxfail = config.getvalue("maxfail")
        self._failed_collection_errors = {}
        self.terminal = reporter()
        self.trdist = None
        self.slaves = {}
        self.test_groups = self._test_item_generator()

    def send(self, slaveid, event_data):
        """Send data to slave.

        ``event_data`` will be serialized as JSON, and so must be JSON serializable

        """
        event_json = json.dumps(event_data)
        self.sock.send_multipart([slaveid, '', event_json])

    def recv(self, *expected_event_names):
        """Receive data from a slave

        Args:
            *expected_event_names: Event names to accept from slaves. Events received that aren't
                in this list indicate a slave in the wrong state, which is a runtime error.

        Raises RuntimeError if unexpected events are received.

        """
        while True:
            slaveid, empty, event_json = self.sock.recv_multipart()
            event_data = json.loads(event_json)
            event_name = event_data.pop('_event_name')

            if event_name == 'message':
                # messages are special, if they're encountered in any recv loop they get printed
                self.print_message(event_data['message'], slaveid)
                self.ack(slaveid, event_name)
            elif event_name not in expected_event_names:
                self.kill(slaveid)
                raise RuntimeError('slave event out of order. Expected one of "%s", got %s' %
                    (', '.join(expected_event_names), event_name)
                )
            else:
                return slaveid, event_data, event_name

    def print_message(self, message, prefix='master'):
        """Print a message from a node to the py.test console

        Args:
            slaveid: Can be a slaveid or any string, e.g. ``'master'`` is also useful here.
            message: The message to print

        """
        # differentiate master and slave messages
        if prefix == 'master':
            markup = {'blue': True}
        else:
            markup = {'cyan': True}
        self.terminal.write_ensure_prefix('(%s) ' % prefix, message, **markup)

    def ack(self, slaveid, event_name):
        """Acknowledge a slave's message"""
        self.send(slaveid, 'ack %s' % event_name)

    def interrupt(self, slaveid):
        """Nicely ask a slave to terminate"""
        slave = self.slaves.pop(slaveid, None)
        if slave:
            slave.send_signal(subprocess.signal.SIGINT)

    def kill(self, slaveid):
        """Rudely kill a slave"""
        slave = self.slaves.pop(slaveid, None)
        if slave:
            slave.kill()

    def send_tests(self, slaveid):
        """Send a slave a group of tests"""
        try:
            tests = self.test_groups.next()
        except StopIteration:
            tests = []
        self.send(slaveid, tests)
        if tests:
            self.print_message('sent %d tests to %s' % (len(tests), slaveid))
        return tests

    @pytest.mark.trylast
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
        self.terminal = reporter(self.config)
        self.trdist = TerminalDistReporter(self.config, self.terminal)
        self.config.pluginmanager.register(self.trdist, "terminaldistreporter")
        self.session = session

        # set up the ipc socket
        zmq_endpoint = 'ipc://%s' % os.path.join(session.fspath.strpath, '.pytest-parallel.ipc')
        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.ROUTER)
        self.sock.bind('%s' % zmq_endpoint)

        # write out the slave config
        # The relies on args and option being easily serializable as yaml.
        # If that stops being the case, look at serialize_/unserialize_ report for another option
        conf.runtime['slave_config'] = {
            'args': self.config.args,
            'options': self.config.option,
            'zmq_endpoint': zmq_endpoint,
        }
        conf.save('slave_config')

        # Fire up the workers
        devnull = open(os.devnull, 'w')
        for i, base_url in enumerate(self.config.option.appliances):
            slaveid = 'slave%d' % i
            # worker output redirected to null; useful info comes via messages and logs
            slave = subprocess.Popen(['python', remote.__file__, slaveid, base_url],
                stdout=devnull, stderr=devnull)
            self.slaves[slaveid] = slave
            atexit.register(_failsafe, slave.kill)

    def pytest_runtestloop(self):
        """pytest runtest loop

        - Disable the master terminal reporter hooks, so we can add our own handlers
          that include the slaveid in the output
        - Send tests to slaves when they ask
        - Log the starting of tests and test results, including slave id
        - Handle clean slave shutdown when they finish their runtest loops
        - Restore the master terminal reporter after testing so we get the final report

        """
        # Build master collection for diffing with slaves
        for item in self.session.items:
            self.collection[item.nodeid] = item

        try:
            slave_collections = []

            # stash this so we don't calculate it every iteration
            # it's only need it for collection diffing
            num_slaves = len(self.slaves)
            self.terminal.rewrite("Waiting for slave collections", red=True)

            while True:
                if not self.slaves:
                    # All slaves are killed or errored, we're done with tests
                    self.session_finished = True
                    break

                slaveid, event_data, event_name = self.recv(
                    'collectionfinish',
                    'need_tests',
                    'runtest_logreport',
                    'runtest_logstart',
                    'sessionfinish'
                )

                if event_name == 'collectionfinish':
                    slave_collections.append(event_data['node_ids'])
                    self.terminal.rewrite(
                        "Received %d collections from slaves" % len(slave_collections), yellow=True)
                    # Don't ack here, leave the slaves blocking on recv
                    # after sending collectionfinish, then sync up when all collections are diffed
                elif event_name == 'need_tests':
                    self.send_tests(slaveid)
                elif event_name == 'runtest_logstart':
                    self.ack(slaveid, event_name)
                    self.trdist.runtest_logstart(slaveid,
                        event_data['nodeid'], event_data['location'])
                elif event_name == 'runtest_logreport':
                    self.ack(slaveid, event_name)
                    report = unserialize_report(event_data['report'])
                    self.trdist.runtest_logreport(slaveid, report)
                elif event_name == 'sessionfinish':
                    self.ack(slaveid, event_name)
                    slave = self.slaves.pop(slaveid)
                    slave.wait()

                # wait for all slave collections to arrive, then diff collections and ack
                if slave_collections is not None:
                    if len(slave_collections) != num_slaves:
                        continue

                    # Turn off the terminal reporter to suppress the builtin logstart printing
                    try:
                        self.config.pluginmanager.unregister(self.terminal)
                    except ValueError:
                        # plugin already disabled
                        pass

                    # compare slave collections to the master, all test ids must be the same
                    self.terminal.rewrite("Received all collections from slaves", green=True)
                    self.log.debug('diffing slave collections')
                    for slave_collection in slave_collections:
                        report_collection_diff(self.collection.keys(), slave_collection, slaveid)

                    # Clear slave collections
                    slave_collections = None

                    # let the slaves continue
                    for slave in self.slaves:
                        self.ack(slave, event_name)

                    self.print_message('Distributing %d tests across %d slaves'
                        % (len(self.collection), num_slaves))
                    self.log.info('starting master test distribution')
        except Exception as ex:
            self.log.error('Exception in runtest loop:')
            self.log.exception(ex)
            raise
        finally:
            # Restore the terminal reporter for exit hooks
            self.config.pluginmanager.register(self.terminal, 'terminalreporter')

        # Suppress other runtestloop calls
        return True

    def _test_item_generator(self):
        for tests in self._modscope_item_generator():
            yield tests

    def _modscope_item_generator(self):
        # breaks out tests by module, can work just about any way we want
        # as long as it yields lists of tests id from the master collection
        sent_tests = 0
        module_items_cache = []
        collection_ids = self.collection.keys()
        collection_len = len(collection_ids)
        for i, item_id in enumerate(collection_ids):
            # everything before the first '::' is the module fspath
            i_fspath = item_id.split('::')[0]
            try:
                nextitem_id = collection_ids[i + 1]
                ni_fspath = nextitem_id.split('::')[0]
            except IndexError:
                nextitem_id = ni_fspath = None

            module_items_cache.append(item_id)
            if i_fspath == ni_fspath:
                # This item and the next item are in the same module
                # loop to the next item
                continue
            else:
                # This item and the next item are in different modules,
                # yield the indices if any items were generated
                if not module_items_cache:
                    continue

                for tests in self._modscope_id_splitter(module_items_cache):
                    tests_len = len(tests)
                    sent_tests += tests_len
                    self.log.info('%d tests remaining to send'
                        % (collection_len - sent_tests))
                    yield tests

                # Then clear the cache in-place
                module_items_cache[:] = []

    def _modscope_id_splitter(self, module_items):
        # given a list of item ids from one test module, break up tests into groups with the same id
        parametrized_ids = defaultdict(list)
        for item in module_items:
            try:
                # split on the leftmost bracket, then strip everything after the rightmight bracket
                # so 'test_module.py::test_name[parametrized_id]' becomes 'parametrized_id'
                parametrized_id = item.split('[')[1].rsplit(']')[0]
            except IndexError:
                # splits failed, item has no parametrized id
                parametrized_id = None
            parametrized_ids[parametrized_id].append(item)

        for id, tests in parametrized_ids.items():
            if id is None:
                id = 'no params'
            self.log.info('sent tests with param %s %r' % (id, tests))
            yield tests


def report_collection_diff(from_collection, to_collection, slaveid):
    """Report differences, if any exist, between master and slave collections

    Raises RuntimeError if collections differ

    Note:

        This function will sort functions before comparing them.

    """
    from_collection, to_collection = sorted(from_collection), sorted(to_collection)
    if from_collection == to_collection:
        # Well, that was easy.
        return True

    # diff the two, so we get some idea of what's wrong
    diff = difflib.unified_diff(
        from_collection,
        to_collection,
        fromfile='master',
        tofile=slaveid,
    )
    # diff is a line generator, stringify it
    diff = '\n'.join([line.rstrip() for line in diff])
    err = '{slaveid} has a different collection than the master\n{diff}'.format(
        slaveid=slaveid, diff=diff)
    raise RuntimeError(err)


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
        test = self.tr._locationline(str(location[0]), *location)
        prefix = '(%s) %s' % (slaveid, test)
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
        test = self.tr._locationline(str(report.location[0]), *report.location)

        prefix = '(%s) %s' % (slaveid, test)
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
