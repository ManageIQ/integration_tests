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
import re
import signal
import subprocess
from collections import OrderedDict, defaultdict, deque, namedtuple
from datetime import datetime
from itertools import count
from threading import Lock, RLock, Thread, Timer
from time import sleep, time
from urlparse import urlparse

import zmq
from _pytest import runner
from functools32 import wraps

from fixtures import terminalreporter
from fixtures.parallelizer import remote
from fixtures.pytest_store import store
from utils import at_exit, conf
from utils.appliance import IPAppliance, stack as appliance_stack
from utils.log import create_sublogger
from utils.net import random_port
from utils.path import conf_path, project_path
from utils.sprout import SproutClient, SproutException
from utils.wait import wait_for


_appliance_help = '''specify appliance URLs to use for distributed testing.
this option can be specified more than once, and must be specified at least two times'''

env_base_urls = conf.env.get('parallel_base_urls', [])
if env_base_urls:
    conf.runtime['env']['base_url'] = env_base_urls[0]

# Initialize slaveid to None, indicating this as the master process
# slaves will set this to a unique string when they're initialized
conf.runtime['env']['slaveid'] = None

# lock for protecting mutation of recv queue
recv_lock = Lock()
# lock for protecting zmq socket access
zmq_lock = Lock()


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group._addoption('--appliance', dest='appliances', action='append',
        default=env_base_urls, metavar='base_url', help=_appliance_help)
    group._addoption('--use-sprout', dest='use_sprout', action='store_true',
        default=False, help="Use Sprout for provisioning appliances.")
    group._addoption('--sprout-appliances', dest='sprout_appliances', type=int,
        default=1, help="How many Sprout appliances to use?.")
    group._addoption('--sprout-timeout', dest='sprout_timeout', type=int,
        default=60, help="How many minutes is the lease timeout.")
    group._addoption('--sprout-provision-timeout', dest='sprout_provision_timeout', type=int,
        default=60, help="How many minutes to wait for appliances provisioned.")
    group._addoption(
        '--sprout-group', dest='sprout_group', default=None, help="Which stream to use.")
    group._addoption(
        '--sprout-version', dest='sprout_version', default=None, help="Which version to use.")
    group._addoption(
        '--sprout-date', dest='sprout_date', default=None, help="Which date to use.")
    group._addoption(
        '--sprout-desc', dest='sprout_desc', default=None, help="Set description of the pool.")


def pytest_addhooks(pluginmanager):
    import hooks
    pluginmanager.add_hookspecs(hooks)


def pytest_configure(config):
    # configures the parallel session, then fires pytest_parallel_configured
    if (config.option.appliances or (config.option.use_sprout and
            config.option.sprout_appliances > 1)):
        session = ParallelSession(config)
        config.pluginmanager.register(session, "parallel_session")
        store.parallelizer_role = 'master'
        config.hook.pytest_parallel_configured(parallel_session=session)
    else:
        config.hook.pytest_parallel_configured(parallel_session=None)


def dump_pool_info(printf, pool_data):
    printf("Fulfilled: {}".format(pool_data["fulfilled"]))
    printf("Progress: {}%".format(pool_data["progress"]))
    printf("Appliances:")
    for appliance in pool_data["appliances"]:
        name = appliance.pop("name")
        printf("\t{}:".format(name))
        for key in sorted(appliance.keys()):
            printf("\t\t{}: {}".format(key, appliance[key]))


def handle_end_session(signal, frame):
    # when signaled, end the current test session immediately
    if store.parallel_session:
        store.parallel_session.session_finished = True
signal.signal(signal.SIGQUIT, handle_end_session)


class SlaveDict(dict):
    """A normal dict, but with a special "add" method that autogenerated slaveids"""
    # intentionally in the class scope so all instances share the slave counter
    slaveid_generator = ('slave{:02d}'.format(i) for i in count())
    lock = RLock()
    _instances = []

    def __init__(self, *args, **kwargs):
        super(SlaveDict, self).__init__(*args, **kwargs)
        with self.lock:
            SlaveDict._instances.append(self)

    # autoincrement the slaveids when something is added
    def add(self, value):
        self[next(self.slaveid_generator)] = value

    # when removing a slave with this method, it is removed from all instances
    # use the normal `del` behavior to only remove from one instances
    def remove(self, key):
        with self.lock:
            for instance in self._instances:
                if key in instance:
                    del(instance[key])

    # helper to wrap dict method wrapper to generate methods protected by a lock
    # like a decorator, but takes a method name instead of wrapping
    def _lock_wrap(method_name):
        wrapped = getattr(dict, method_name)

        @wraps(wrapped)
        def wrapper(self, *args, **kwargs):
            with self.lock:
                return wrapped(self, *args, **kwargs)
        return wrapper
    # all mutating methods should be wrapped; if one is missing here that isn't intentional
    __setitem__ = _lock_wrap('__setitem__')
    __delitem__ = _lock_wrap('__delitem__')
    # destroy now-useless lock wrapper function
    del(_lock_wrap)


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
        self.pool_lock = Lock()
        from utils.conf import cfme_data
        self.provs = sorted(set(cfme_data['management_systems'].keys()),
                            key=len, reverse=True)
        self.slave_allocation = collections.defaultdict(list)
        self.used_prov = set()

        self.failed_slave_test_groups = deque()
        self.slave_spawn_count = 0
        self.sprout_client = None
        self.sprout_timer = None
        self.sprout_pool = None
        if not self.config.option.use_sprout:
            # Without Sprout
            self.appliances = self.config.option.appliances
        else:
            # Using sprout
            self.sprout_client = SproutClient.from_config()
            try:
                if self.config.option.sprout_desc is not None:
                    jenkins_job = re.findall(r"Jenkins.*[^\d+$]", self.config.option.sprout_desc)
                    if jenkins_job:
                        self.terminal.write(
                            "Check if pool already exists for this '{}' Jenkins job\n".format(
                                jenkins_job[0]))
                        jenkins_job_pools = self.sprout_client.find_pools_by_description(
                            jenkins_job[0], partial=True)
                        for pool in jenkins_job_pools:
                            self.terminal.write("Destroying the old pool {} for '{}' job.\n".format(
                                pool, jenkins_job[0]))
                            self.sprout_client.destroy_pool(pool)
            except Exception as e:
                self.terminal.write(
                    "Exception occurred during old pool deletion, this can be ignored"
                    "proceeding to Request new pool")
                self.terminal.write("> The exception was: {}".format(str(e)))

            self.terminal.write(
                "Requesting {} appliances from Sprout at {}\n".format(
                    self.config.option.sprout_appliances, self.sprout_client.api_entry))
            pool_id = self.sprout_client.request_appliances(
                self.config.option.sprout_group,
                count=self.config.option.sprout_appliances,
                version=self.config.option.sprout_version,
                date=self.config.option.sprout_date,
                lease_time=self.config.option.sprout_timeout
            )
            self.terminal.write("Pool {}. Waiting for fulfillment ...\n".format(pool_id))
            self.sprout_pool = pool_id
            at_exit(self.sprout_client.destroy_pool, self.sprout_pool)
            if self.config.option.sprout_desc is not None:
                self.sprout_client.set_pool_description(
                    pool_id, str(self.config.option.sprout_desc))
            try:
                result = wait_for(
                    lambda: self.sprout_client.request_check(self.sprout_pool)["fulfilled"],
                    num_sec=self.config.option.sprout_provision_timeout * 60,
                    delay=5,
                    message="requesting appliances was fulfilled"
                )
            except:
                pool = self.sprout_client.request_check(self.sprout_pool)
                dump_pool_info(lambda x: self.terminal.write("{}\n".format(x)), pool)
                self.terminal.write("Destroying the pool on error.\n")
                self.sprout_client.destroy_pool(pool_id)
                raise
            else:
                pool = self.sprout_client.request_check(self.sprout_pool)
                dump_pool_info(lambda x: self.terminal.write("{}\n".format(x)), pool)
            self.terminal.write("Provisioning took {0:.1f} seconds\n".format(result.duration))
            request = self.sprout_client.request_check(self.sprout_pool)
            self.appliances = []
            # Push an appliance to the stack to have proper reference for test collection
            # FIXME: this is a bad hack based on the need for controll of collection partitioning
            appliance_stack.push(
                IPAppliance(address=request["appliances"][0]["ip_address"]))
            self.terminal.write("Appliances were provided:\n")
            for appliance in request["appliances"]:
                url = "https://{}/".format(appliance["ip_address"])
                self.appliances.append(url)
                self.terminal.write("- {} is {}\n".format(url, appliance['name']))
            map(lambda a: "https://{}/".format(a["ip_address"]), request["appliances"])
            self._reset_timer()
            # Set the base_url for collection purposes on the first appliance
            conf.runtime["env"]["base_url"] = self.appliances[0]
            # Retrieve and print the template_name for Jenkins to pick up
            template_name = request["appliances"][0]["template_name"]
            conf.runtime["cfme_data"]["basic_info"]["appliance_template"] = template_name
            self.terminal.write("appliance_template=\"{}\";\n".format(template_name))
            with project_path.join('.appliance_template').open('w') as template_file:
                template_file.write('export appliance_template="{}"'.format(template_name))
            self.terminal.write("Parallelized Sprout setup finished.\n")
            self.slave_appliances_data = {}
            for appliance in request["appliances"]:
                self.slave_appliances_data[appliance["ip_address"]] = (
                    appliance["template_name"], appliance["provider"]
                )

        # set up the ipc socket
        zmq_endpoint = 'tcp://127.0.0.1:{}'.format(random_port())
        ctx = zmq.Context.instance()
        self.sock = ctx.socket(zmq.ROUTER)
        self.sock.bind('{}'.format(zmq_endpoint))

        # clean out old slave config if it exists
        slave_config = conf_path.join('slave_config.yaml')
        slave_config.check() and slave_config.remove()

        # write out the slave config
        conf.runtime['slave_config'] = {
            'args': self.config.args,
            'options': self.config.option.__dict__,
            'zmq_endpoint': zmq_endpoint,
            'sprout': self.sprout_client is not None and self.sprout_pool is not None,
        }
        if hasattr(self, "slave_appliances_data"):
            conf.runtime['slave_config']["appliance_data"] = self.slave_appliances_data
        conf.runtime['slave_config']['options']['use_sprout'] = False  # Slaves don't use sprout
        conf.save('slave_config')

        for i, base_url in enumerate(self.appliances):
            self.slave_urls.add(base_url)

        for slave in sorted(self.slave_urls):
            self.print_message("using appliance {}".format(self.slave_urls[slave]),
                slave, green=True)

        # Start the recv queue
        self._recv_queue = deque()
        recv_queuer = Thread(target=_recv_queue, args=(self,))
        recv_queuer.daemon = True
        recv_queuer.start()

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
                    with SlaveDict.lock:
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
            ['python', remote.__file__, slaveid, base_url],
            stdout=devnull, stderr=devnull,
        )
        self.slaves[slaveid] = slave
        self.slave_spawn_count += 1
        at_exit(slave.kill)

    def _reset_timer(self):
        if not (self.sprout_client is not None and self.sprout_pool is not None):
            if self.sprout_timer:
                self.sprout_timer.cancel()  # Cancel it anyway
                self.terminal.write("Sprout timer cancelled\n")
            return
        if self.sprout_timer:
            self.sprout_timer.cancel()
        self.sprout_timer = Timer(
            (self.config.option.sprout_timeout / 2) * 60,
            self.sprout_ping_pool)
        self.sprout_timer.daemon = True
        self.sprout_timer.start()

    def sprout_ping_pool(self):
        try:
            self.sprout_client.prolong_appliance_pool_lease(self.sprout_pool)
        except SproutException as e:
            self.terminal.write(
                "Pool {} does not exist any more, disabling the timer.\n".format(self.sprout_pool))
            self.terminal.write(
                "This can happen before the tests are shut down "
                "(last deleted appliance deleted the pool")
            self.terminal.write("> The exception was: {}".format(str(e)))
            self.sprout_pool = None  # Will disable the timer in next reset call.
        self._reset_timer()

    def send(self, slaveid, event_data):
        """Send data to slave.

        ``event_data`` will be serialized as JSON, and so must be JSON serializable

        """
        event_json = json.dumps(event_data)
        with zmq_lock:
            self.sock.send_multipart([slaveid, '', event_json])

    def recv(self):
        """Return any unproccesed events from the recv queue"""
        try:
            with recv_lock:
                return self._recv_queue.popleft()
        except IndexError:
            return None, None, None

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
        shutdown_thread = Thread(target=self._monitor_shutdown_t, args=(slaveid, respawn))
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
            with SlaveDict.lock:
                tests = list(self.failed_slave_test_groups.popleft())
        except IndexError:
            try:
                tests = self.get(slaveid)
                # To return to the old parallelizer distributor, remove the line above
                # and replace it with the line below.
                # tests = self.test_groups.next()
            except StopIteration:
                tests = []

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
        for item in self.session.items:
            self.collection[item.nodeid] = item

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
                if event_name == 'collectionfinish':
                    slave_collection = event_data['node_ids']
                    # compare slave collection to the master, all test ids must be the same
                    self.log.debug('diffing {} collection'.format(slaveid))
                    diff_err = report_collection_diff(slaveid, self.collection.keys(),
                        slave_collection)
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
                    if (report.when in ('call', 'teardown')
                            and report.nodeid in self.slave_tests[slaveid]):
                        self.slave_tests[slaveid].remove(report.nodeid)
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
                    if tests:
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
            self.log.info('sent tests with param {} {!r}'.format(id, tests))
            yield tests

    def get(self, slave):
        with self.pool_lock:
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
                raise StopIteration
            current_allocate = self.slave_allocation.get(slave, None)
            # num_provs_list = [len(v) for k, v in self.slave_allocation.iteritems()]
            # average_num_provs = sum(num_provs_list) / float(len(self.slaves))
            appliance_num_limit = 2
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


def _recv_queue(session):
    # poll the zmq socket, populate the recv queue deque with responses
    while not session.session_finished:
        try:
            with zmq_lock:
                slaveid, empty, event_json = session.sock.recv_multipart(flags=zmq.NOBLOCK)
        except zmq.Again:
            continue
        event_data = json.loads(event_json)
        event_name = event_data.pop('_event_name')

        if event_name == 'message':
            message = event_data.pop('message')
            # messages are special, handle them immediately
            session.print_message(message, slaveid, **event_data)
            session.ack(slaveid, event_name)
        else:
            with recv_lock:
                session._recv_queue.append((slaveid, event_data, event_name))


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
