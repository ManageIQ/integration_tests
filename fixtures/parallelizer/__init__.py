import difflib
import Queue as queue
from collections import OrderedDict

import execnet
import py
import pytest
from _pytest import runner

from fixtures.terminalreporter import reporter
from utils.conf import env, runtime
from utils.log import create_sublogger


_appliance_help = '''specify appliance URLs to use for distributed testing.
this option can be specified more than once, and must be specified at least two times'''

env_base_urls = env.get('parallel_base_urls', [])
if env_base_urls:
    runtime['env']['base_url'] = env_base_urls[0]

# Initialize slaveid to None, indicating this as the master process
# slaves will set this to a unique string when they're initialized
runtime['env']['slaveid']


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group._addoption('--appliance', dest='appliances', action='append',
        default=env_base_urls, metavar='base_url', help=_appliance_help)

# -------------------------------------------------------------------------
# distributed testing initialization
# -------------------------------------------------------------------------


def pytest_configure(config, __multicall__):
    __multicall__.execute()
    # TODO: Wrap in a conditional based on the number of appliances for testing
    if len(config.option.appliances) > 1:
        session = DSession(config)
        config.pluginmanager.register(session, "dsession")


class Interrupted(KeyboardInterrupt):
    """ signals an immediate interruption. """


class DSession(object):
    def __init__(self, config):
        self.config = config
        self.shuttingdown = False
        self.countfailures = 0
        self.log = create_sublogger('dsession')
        self.maxfail = config.getvalue("maxfail")
        self.queue = queue.Queue()
        self._failed_collection_errors = {}
        self.terminal = reporter()
        self.trdist = TerminalDistReporter(config)
        config.pluginmanager.register(self.trdist, "terminaldistreporter")

    def report_line(self, line):
        if self.terminal and self.config.option.verbose >= 0:
            self.terminal.write_line(line)

    @pytest.mark.trylast
    def pytest_sessionstart(self, session):
        # If reporter() gave us a fake terminal reporter in __init__, the real
        # terminal reporter is registered by now
        self.terminal = reporter()
        self.nodemanager = NodeManager(self.config)
        self.nodemanager.setup_nodes(putevent=self.queue.put)

    def pytest_sessionfinish(self, session):
        """ teardown any resources after a test run. """
        # if not fully initialized
        nm = getattr(self, 'nodemanager', None)
        if nm is not None:
            nm.teardown_nodes()

    def pytest_collection(self):
        # prohibit collection of test items in master process
        return True

    def pytest_runtestloop(self):
        # Should be one node per appliance
        numnodes = len(self.nodemanager.specs)
        self.sched = ModscopeScheduling(numnodes)
        self.shouldstop = False
        self.session_finished = False
        while not self.session_finished:
            self.loop_once()
            if self.shouldstop:
                raise Interrupted(str(self.shouldstop))
        return True

    def loop_once(self):
        """ process one callback from one of the slaves. """
        while 1:
            try:
                eventcall = self.queue.get(timeout=2.0)
                break
            except queue.Empty:
                continue
        callname, kwargs = eventcall
        assert callname, kwargs
        method = "slave_" + callname
        call = getattr(self, method)
        self.log.debug("calling method: %s(**%s)" % (method, kwargs))
        call(**kwargs)
        if self.sched.tests_finished():
            self.triggershutdown()

    #
    # callbacks for processing events from slaves
    #

    def slave_slaveready(self, node, slaveinfo):
        node.slaveinfo = slaveinfo
        node.slaveinfo['id'] = node.gateway.id
        node.slaveinfo['spec'] = node.gateway.spec
        self.trdist.testnodeready(node)
        self.sched.addnode(node)
        if self.shuttingdown:
            node.shutdown()

    def slave_slavefinished(self, node):
        self.trdist.testnodedown(node, None)
        # keyboard-interrupt
        if node.slaveoutput['exitstatus'] == 2:
            self.shouldstop = "%s received keyboard-interrupt" % (node,)
            self.slave_errordown(node, "keyboard-interrupt")
            return
        self.sched.remove_node(node)
        # assert not crashitem, (crashitem, node)
        if self.shuttingdown and not self.sched.hasnodes():
            self.session_finished = True

        # self.send_tests(node)

    def slave_errordown(self, node, error):
        self.trdist.testnodedown(node, error)
        try:
            crashitem = self.sched.remove_node(node)
        except KeyError:
            pass
        else:
            if crashitem:
                self.handle_crashitem(crashitem, node)
                # self.report_line("item crashed on node: %s" % crashitem)
        if not self.sched.hasnodes():
            self.session_finished = True

    def slave_collectionfinish(self, node, ids):
        self.sched.addnode_collection(node, ids)
        if self.terminal:
            self.trdist.setstatus(node.gateway.spec, "[%d]" % (len(ids)))

        if self.sched.collection_is_completed:
            if self.terminal:
                self.trdist.ensure_show_status()
                self.terminal.write_line("")
                self.terminal.write_line("scheduling tests via %s" % (
                    self.sched.__class__.__name__))

            self.sched.init_distribute()

    def slave_logstart(self, node, nodeid, location):
        self.config.hook.pytest_runtest_logstart(
            nodeid=nodeid, location=location)

    def slave_testreport(self, node, rep):
        if not (rep.passed and rep.when != "call"):
            if rep.when in ("setup", "call"):
                self.sched.remove_item(node, rep.item_index, rep.duration)
        # self.report_line("testreport %s: %s" %(rep.id, rep.status))
        rep.node = node
        self.config.hook.pytest_runtest_logreport(report=rep)
        self._handlefailures(rep)

    def slave_collectreport(self, node, rep):
        if rep.failed:
            self._failed_slave_collectreport(node, rep)

    def slave_needs_tests(self, node):
        self.sched.send_tests(node)

    def slave_message(self, node, message):
        self.trdist.nodemessage(node, message)

    def _failed_slave_collectreport(self, node, rep):
        # Check we haven't already seen this report (from
        # another slave).
        if rep.longrepr not in self._failed_collection_errors:
            self._failed_collection_errors[rep.longrepr] = True
            self.config.hook.pytest_collectreport(report=rep)
            self._handlefailures(rep)

    def _handlefailures(self, rep):
        if rep.failed:
            self.countfailures += 1
            if self.maxfail and self.countfailures >= self.maxfail:
                self.shouldstop = "stopping after %d failures" % (
                    self.countfailures)

    def triggershutdown(self):
        self.log.debug("triggering shutdown")
        self.shuttingdown = True
        for node in self.sched.node2pending:
            node.shutdown()

    def handle_crashitem(self, nodeid, slave):
        # XXX get more reporting info by recording pytest_runtest_logstart?
        my_runner = self.config.pluginmanager.getplugin("runner")
        fspath = nodeid.split("::")[0]
        msg = "Slave %r crashed while running %r" % (slave.gateway.id, nodeid)
        rep = my_runner.TestReport(nodeid, (fspath, None, fspath), (),
            "failed", msg, "???")
        rep.node = slave
        self.config.hook.pytest_runtest_logreport(report=rep)


class ModscopeScheduling(object):
    # Based on xdist's LoadScheduling, but tests are split among processes by test module
    def __init__(self, numnodes):
        self.numnodes = numnodes
        self.node2pending = OrderedDict()
        self.node2collection = OrderedDict()
        self.log = create_sublogger('scheduler')
        self.pending = []
        self.collection_is_completed = False
        self.module_testindex_gen = None

    def hasnodes(self):
        return bool(self.node2pending)

    def addnode(self, node):
        self.node2pending[node] = []

    def tests_finished(self):
        if not self.collection_is_completed or self.pending:
            self.log.debug('pending: %r' % self.pending)
            return False
        # for items in self.node2pending.values():
        #    if items:
        #        return False
        return True

    def addnode_collection(self, node, collection):
        self.log.debug('addnode collection: %r', collection)
        assert not self.collection_is_completed
        assert node in self.node2pending
        self.node2collection[node] = list(collection)
        if len(self.node2collection) >= self.numnodes:
            self.collection_is_completed = True

    def remove_item(self, node, item_index, duration=0):
        node_pending = self.node2pending[node]
        node_pending.remove(item_index)
        # pre-load items-to-test if the node may become ready
        self.log.debug('node2pending: %r' % node_pending)

        if self.pending:
            if duration >= 0.1 and node_pending:
                # seems the node is doing long-running tests
                # so let's rather wait with sending new items
                return

        self.log.info("num items waiting for node: %d", len(self.pending))

    def remove_node(self, node):
        pending = self.node2pending.pop(node)
        if not pending:
            return
        # the node must have crashed on the item if there are pending ones
        crashitem = self.collection[pending.pop(0)]
        self.pending.extend(pending)
        return crashitem

    def init_distribute(self):
        assert self.collection_is_completed
        # XXX allow nodes to have different collections
        node_collection_items = list(self.node2collection.items())
        first_node, col = node_collection_items[0]
        for node, collection in node_collection_items[1:]:
            report_collection_diff(
                col,
                collection,
                first_node.gateway.id,
                node.gateway.id,
            )

        self.collection = col
        self.pending[:] = range(len(col))
        if not col:
            return

        for node in self.node2pending:
            self.send_tests(node)

    # f = open("/tmp/sent", "w")
    def send_tests(self, node):
        if self.module_testindex_gen is None:
            self.module_testindex_gen = self._modscope_item_generator(self.pending, self.collection)

        try:
            test_indices = self.module_testindex_gen.next()
            node.send_runtest_some(test_indices)
            del self.pending[:len(test_indices)]
            self.node2pending[node].extend(test_indices)
            self.log.debug('left to send: %d tests' % len(self.pending))
        except StopIteration:
            self.log.debug('ran out of tests!')

    def _modscope_item_generator(self, indices, collection):
        # Make local copies on instantiation
        indices = list(indices)
        collection = list(collection)
        sent_tests = 0
        module_indices_cache = []
        for i in indices:
            # collection is a list of nodeids
            # everything before the first '::' is the module fspath
            i_fspath = collection[i].split('::')[0]
            try:
                ni_fspath = collection[i + 1].split('::')[0]
            except IndexError:
                # collection[i+1] didn't exist, this is the last test item
                ni_fspath = None

            module_indices_cache.append(i)
            if i_fspath == ni_fspath:
                # This item and the next item are in the same module
                # loop to the next item
                continue
            else:
                # This item and the next item are in different modules,
                # yield the indices if any items were generated
                cache_len = len(module_indices_cache)
                if cache_len > 0:
                    sent_tests += cache_len
                    self.log.info('sending %d tests for module %s, %d tests remaining to send' %
                        (cache_len, i_fspath, len(collection) - sent_tests))
                    yield module_indices_cache

                    # Then clear the cache in-place
                    module_indices_cache[:] = []


def report_collection_diff(from_collection, to_collection, from_id, to_id):
    """Report the collected test difference between two nodes.

    :returns: True if collections are equal.

    :raises: AssertionError with a detailed error message describing the
             difference between the collections.

    """
    if from_collection == to_collection:
        return True

    diff = difflib.unified_diff(
        from_collection,
        to_collection,
        fromfile=from_id,
        tofile=to_id,
    )
    error_message = py.builtin._totext(
        'Different tests were collected between {from_id} and {to_id}. '
        'The difference is:\n'
        '{diff}'
    ).format(from_id=from_id, to_id=to_id, diff='\n'.join(diff))
    msg = "\n".join([x.rstrip() for x in error_message.split("\n")])
    raise AssertionError(msg)


class TerminalDistReporter(object):
    def __init__(self, config):
        self.config = config
        self.tr = reporter(config)
        self._status = {}
        self._lastlen = 0

    def write_line(self, msg):
        self.tr.write_line(msg)

    def ensure_show_status(self):
        if not self.tr.hasmarkup:
            self.write_line(self.getstatus())

    def setstatus(self, spec, status, show=True):
        self._status[spec.id] = status
        if show and self.tr.hasmarkup:
            self.rewrite(self.getstatus())

    def getstatus(self):
        parts = ["%s %s" % (spec.id, self._status[spec.id]) for spec in self._specs]
        return " / ".join(parts)

    def rewrite(self, line, newline=False):
        pline = line + " " * max(self._lastlen - len(line), 0)
        if newline:
            self._lastlen = 0
            pline += "\n"
        else:
            self._lastlen = len(line)
        self.tr.rewrite(pline, bold=True)

    def setupnodes(self, specs):
        self._specs = specs
        for spec in specs:
            self.setstatus(spec, "I", show=False)
        self.setstatus(spec, "I", show=True)
        self.ensure_show_status()

    def newgateway(self, gateway):
        if self.config.option.verbose > 0:
            rinfo = gateway._rinfo()
            version = "%s.%s.%s" % rinfo.version_info[:3]
            self.rewrite("[%s] %s Python %s cwd: %s" % (
                gateway.id, rinfo.platform, version, rinfo.cwd),
                newline=True)
        self.setstatus(gateway.spec, "C")

    def testnodeready(self, node):
        if self.config.option.verbose > 0:
            d = node.slaveinfo
            infoline = "[%s] Python %s" % (
                d['id'],
                d['version'].replace('\n', ' -- ')
            )
            self.rewrite(infoline, newline=True)
        self.setstatus(node.gateway.spec, "ok")

    def testnodedown(self, node, error):
        if not error:
            return
        self.write_line("[%s] node down: %s" % (node.gateway.id, error))

    def nodemessage(self, node, message):
        self.write_line("[%s] %s" % (node.gateway.id, message))


class NodeManager(object):
    EXIT_TIMEOUT = 10

    def __init__(self, config, specs=None, defaultchdir="pyexecnetcache"):
        self.config = config
        self._nodesready = py.std.threading.Event()
        self.trace = self.config.trace.get("nodemanager")
        self.log = create_sublogger('nodeman')
        self.group = execnet.Group()
        self.specs = self._getxspecs()
        for spec in self.specs:
            self.group.allocate_id(spec)

    def makegateways(self):
        assert not list(self.group)
        trdist = self.config.pluginmanager.getplugin("terminaldistreporter")
        trdist.setupnodes(self.specs)
        for spec in self.specs:
            gw = self.group.makegateway(spec)
            trdist.newgateway(gw)

    def setup_nodes(self, putevent):
        self.makegateways()
        self.trace("setting up nodes")
        for i, gateway in enumerate(self.group):
            base_url = self.config.option.appliances[i]
            node = SlaveController(self, gateway, self.config, putevent, base_url)
            gateway.node = node  # to keep node alive
            node.setup()
            self.trace("started node %r" % node)

    def teardown_nodes(self):
        self.group.terminate(self.EXIT_TIMEOUT)

    def _getxspecs(self):
        appliances = self.config.option.appliances
        numprocesses = len(appliances)
        gateway_spec = 'popen//dont_write_bytecode'
        if numprocesses > 1:
            return [execnet.XSpec(spec) for spec in [gateway_spec] * numprocesses]
        else:
            if appliances:
                self.log.warning('')
            return []


class SlaveController(object):
    ENDMARK = -1

    def __init__(self, nodemanager, gateway, config, putevent, base_url=None):
        self.nodemanager = nodemanager
        self.putevent = putevent
        self.gateway = gateway
        self.config = config
        self.slaveinput = {'slaveid': gateway.id, 'base_url': base_url}
        self.log = create_sublogger('cmd-%s' % gateway.id)
        self._down = False

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.gateway.id)

    def setup(self):
        from fixtures.parallelizer import remote

        self.log.info("setting up slave session")
        spec = self.gateway.spec
        args = self.config.args
        option_dict = vars(self.config.option)
        if spec.popen:
            name = "popen-%s" % self.gateway.id
            basetemp = self.config._tmpdirhandler.getbasetemp()
            option_dict['basetemp'] = str(basetemp.join(name))
        self.channel = self.gateway.remote_exec(remote)
        self.channel.send((self.slaveinput, args, option_dict))
        if self.putevent:
            self.channel.setcallback(self.process_from_remote,
                endmarker=self.ENDMARK)

    def ensure_teardown(self):
        if hasattr(self, 'channel'):
            if not self.channel.isclosed():
                self.log.info("closing", self.channel)
                self.channel.close()
            # del self.channel
        if hasattr(self, 'gateway'):
            self.log.info("exiting", self.gateway)
            self.gateway.exit()
            # del self.gateway

    def send_runtest_some(self, indices):
        self.sendcommand("runtests", indices=indices)

    def send_runtest_all(self):
        self.sendcommand("runtests_all")

    def shutdown(self):
        if not self._down:
            try:
                self.sendcommand("shutdown")
            except IOError:
                pass

    def sendcommand(self, name, **kwargs):
        """ send a named parametrized command to the other side. """
        self.log.debug("sending command %s(**%s)" % (name, kwargs))
        self.channel.send((name, kwargs))

    def notify_inproc(self, eventname, **kwargs):
        self.log.debug("queuing %s(**%s)" % (eventname, kwargs))
        self.putevent((eventname, kwargs))

    def process_from_remote(self, eventcall):
        """ this gets called for each object we receive from
            the other side and if the channel closes.

            Note that channel callbacks run in the receiver
            thread of execnet gateways - we need to
            avoid raising exceptions or doing heavy work.
        """
        try:
            if eventcall == self.ENDMARK:
                err = self.channel._getremoteerror()
                if not self._down:
                    if not err or isinstance(err, EOFError):
                        # lost connection?
                        err = "Not properly terminated"
                    self.notify_inproc("errordown", node=self, error=err)
                    self._down = True
                return
            eventname, kwargs = eventcall
            if eventname in ("collectionstart"):
                self.log.debug("ignoring %s(%s)" % (eventname, kwargs))
            elif eventname == "slaveready":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname == "slavefinished":
                self._down = True
                self.slaveoutput = kwargs['slaveoutput']
                self.notify_inproc("slavefinished", node=self)
            elif eventname == "logstart":
                self.notify_inproc(eventname, node=self, **kwargs)
            elif eventname in ("testreport", "collectreport", "teardownreport"):
                item_index = kwargs.pop("item_index", None)
                rep = unserialize_report(eventname, kwargs['data'])
                if item_index is not None:
                    rep.item_index = item_index
                self.notify_inproc(eventname, node=self, rep=rep)
            elif eventname == "collectionfinish":
                self.notify_inproc(eventname, node=self, ids=kwargs['ids'])
            elif eventname == "needs_tests":
                self.notify_inproc(eventname, node=self)
            elif eventname == "message":
                self.notify_inproc(eventname, node=self, message=kwargs['message'])
            else:
                raise ValueError("unknown event: %s" % eventname)
        except KeyboardInterrupt:
            # should not land in receiver-thread
            raise
        except:
            excinfo = py.code.ExceptionInfo()
            py.builtin.print_("!" * 20, excinfo)
            self.config.pluginmanager.notify_exception(excinfo)


def unserialize_report(name, reportdict):
    if name == "testreport":
        return runner.TestReport(**reportdict)
    elif name == "collectreport":
        return runner.CollectReport(**reportdict)
